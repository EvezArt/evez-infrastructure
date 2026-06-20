#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python
"""
EVEZ Voice Synth — Fast pipeline for live Telegram conversations.

Primary: Edge TTS (Microsoft) — ~2s latency, American Western voice
Fallback: Coqui XTTS-v2 — ~25s, cloned voice (only if EDGE fails)

Voice: en-US-BrianNeural — Casual, approachable, American, slight Western tinge
"""
import sys
import os
import subprocess
import asyncio
from pathlib import Path

WORKSPACE = Path("/home/openclaw/.openclaw/workspace")
VENV_PYTHON = str(WORKSPACE / "voice-venv" / "bin" / "python")
SAMPLE_DIR = WORKSPACE / "evez-voice" / "samples"

# American Western-tinged voices, prioritized
EDGE_VOICES = [
    "en-US-BrianNeural",        # Approachable, casual, sincere — Western feel
    "en-US-AndrewNeural",       # Warm, confident, authentic
    "en-US-ChristopherNeural",  # Reliable, authority
    "en-US-EricNeural",         # Rational
]


async def edge_tts_synth(text, output_path, voice=None):
    """Synthesize using Edge TTS — ultra fast, ~2s."""
    import edge_tts

    voice = voice or EDGE_VOICES[0]
    communicate = edge_tts.Communicate(text, voice)

    # Write directly to MP3 — no ffmpeg conversion needed
    await communicate.save(output_path)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
        return True
    return False


def xtts_fallback(text, output_path):
    """Fallback to Coqui XTTS-v2 if Edge TTS fails — ~25s."""
    samples = list(SAMPLE_DIR.glob("*.wav")) + list(SAMPLE_DIR.glob("*.mp3"))
    if not samples:
        return False

    # Pick longest sample
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
import sys
from TTS.api import TTS
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=False)
tts.tts_to_file(
    text={repr(text)},
    speaker_wav={repr(best)},
    language='en',
    file_path={repr(output_path)}
)
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", script],
        capture_output=True, text=True, timeout=120
    )
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

    # Ensure output is MP3
    if not output_path.endswith(".mp3"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp3"

    # Try Edge TTS first (fast path)
    try:
        loop = asyncio.new_event_loop()
        success = loop.run_until_complete(edge_tts_synth(text, output_path))
        loop.close()
        if success:
            # Overwrite the original output path if caller expected a different extension
            sys.exit(0)
    except Exception as e:
        print(f"Edge TTS failed: {e}", file=sys.stderr)

    # Fallback to XTTS-v2
    if xtts_fallback(text, output_path):
        sys.exit(0)

    print("All TTS methods failed", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
