#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python
"""
EVEZ Voice Synth — Fast pipeline for live Telegram conversations.

Priority:
1. Local XTTS-v2 server (if running) — ~5s, YOUR cloned voice
2. Edge TTS (Microsoft) — ~2s, BrianNeural as fallback
3. XTTS-v2 inline — ~25s, last resort (loads model fresh)
"""
import sys
import os
import subprocess
import asyncio
import json
import urllib.request
from pathlib import Path

WORKSPACE = Path("/home/openclaw/.openclaw/workspace")
VENV_PYTHON = str(WORKSPACE / "voice-venv" / "bin" / "python")
SAMPLE_DIR = WORKSPACE / "evez-voice" / "samples"
XTTS_SERVER = "http://127.0.0.1:5000"
EDGE_VOICE = "en-US-BrianNeural"


def check_xtts_server():
    """Check if the persistent XTTS server is running."""
    try:
        req = urllib.request.Request(f"{XTTS_SERVER}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def synth_via_xtts_server(text, output_path):
    """Synthesize via the persistent XTTS server — ~5s, your cloned voice."""
    try:
        payload = json.dumps({"text": text, "output": output_path}).encode()
        req = urllib.request.Request(
            f"{XTTS_SERVER}/synthesize",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "ok" and os.path.exists(output_path):
                return True
    except Exception as e:
        print(f"XTTS server failed: {e}", file=sys.stderr)
    return False


async def edge_tts_synth(text, output_path):
    """Synthesize using Edge TTS — ~2s fallback."""
    import edge_tts
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await communicate.save(output_path)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 100


def xtts_inline(text, output_path):
    """Inline XTTS-v2 — ~25s, last resort."""
    samples = list(SAMPLE_DIR.glob("*.wav")) + list(SAMPLE_DIR.glob("*.mp3"))
    if not samples:
        return False
    best = None
    best_dur = 0
    for f in samples:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(f)],
                capture_output=True, text=True, timeout=10
            )
            dur = float(result.stdout.strip())
            if dur > best_dur:
                best_dur = dur
                best = str(f)
        except Exception:
            if best is None:
                best = str(f)
    if not best:
        return False
    script = f"""
from TTS.api import TTS
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=False)
tts.tts_to_file(text={repr(text)}, speaker_wav={repr(best)}, language='en', file_path={repr(output_path)})
"""
    result = subprocess.run([VENV_PYTHON, "-c", script], capture_output=True, text=True, timeout=120)
    return result.returncode == 0 and os.path.exists(output_path)


def main():
    if len(sys.argv) < 3:
        print("Usage: evez-voice-synth.py <output_path> <text>", file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1]
    text = " ".join(sys.argv[2:])

    if not text.strip():
        print("Empty text", file=sys.stderr)
        sys.exit(1)

    if not output_path.endswith(".mp3"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp3"

    # Priority 1: XTTS-v2 server (your cloned voice, ~8s)
    if check_xtts_server():
        mp3_path = output_path  # Server now outputs MP3 directly
        if synth_via_xtts_server(text, mp3_path):
            if os.path.exists(mp3_path):
                sys.exit(0)

    # Priority 2: Edge TTS (fast fallback, ~2s)
    try:
        loop = asyncio.new_event_loop()
        success = loop.run_until_complete(edge_tts_synth(text, output_path))
        loop.close()
        if success:
            sys.exit(0)
    except Exception as e:
        print(f"Edge TTS failed: {e}", file=sys.stderr)

    # Priority 3: Inline XTTS-v2 (last resort, ~25s)
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"
    if xtts_inline(text, wav_path):
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-ar", "44100", "-ac", "1",
             "-b:a", "128k", output_path],
            capture_output=True, timeout=30
        )
        if os.path.exists(output_path):
            sys.exit(0)

    print("All TTS methods failed", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
