#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python3
"""
EVEZ Voice Server — Persistent XTTS-v2 server for low-latency voice cloning.

Loads the model ONCE at startup, then serves synthesis requests via HTTP.
This eliminates the 12s model reload penalty — synthesis only takes ~5s.

Usage:
  python3 evez-voice-server.py [--port 5000]

Then from the synth script:
  curl -X POST http://localhost:5000/synthesize \
    -d '{"text": "Hello", "output": "/tmp/out.wav"}'
"""
import argparse
import os
import sys
import time
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load TTS once at startup
print("Loading XTTS-v2 model (this takes ~12s, one time only)...")
t0 = time.time()
from TTS.api import TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
t1 = time.time()
print(f"Model loaded in {t1-t0:.1f}s — ready for synthesis")

SAMPLE_DIR = Path("/home/openclaw/.openclaw/workspace/evez-voice/samples")


def find_best_sample():
    """Find the longest voice sample."""
    best = None
    best_dur = 0
    for f in list(SAMPLE_DIR.glob("*.wav")) + list(SAMPLE_DIR.glob("*.mp3")):
        try:
            import subprocess
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
    return best


REFERENCE_AUDIO = find_best_sample()
print(f"Reference audio: {REFERENCE_AUDIO}")


class VoiceHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/synthesize":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length).decode())
            text = body.get("text", "")
            output_path = body.get("output", "/tmp/evez_out.wav")

            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "no text"}).encode())
                return

            try:
                t_start = time.time()
                # Output directly to the target path (WAV)
                tts.tts_to_file(
                    text=text,
                    speaker_wav=REFERENCE_AUDIO,
                    language="en",
                    file_path=output_path,
                )
                # Auto-convert to MP3 if WAV was output
                mp3_path = output_path.rsplit('.', 1)[0] + '.mp3'
                if output_path.endswith('.wav'):
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', output_path, '-ar', '44100', '-ac', '1', '-b:a', '128k', mp3_path],
                        capture_output=True, timeout=15
                    )
                    if os.path.exists(mp3_path):
                        os.rename(mp3_path, output_path)
                elapsed = time.time() - t_start

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "output": output_path,
                    "elapsed_s": round(elapsed, 1),
                }).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "model": "xtts_v2"}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "model": "xtts_v2", "reference": REFERENCE_AUDIO}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), VoiceHandler)
    print(f"\nEVEZ Voice Server running on http://127.0.0.1:{args.port}")
    print(f"  POST /synthesize  — synthesize speech in your voice")
    print(f"  GET  /health      — health check")
    print(f"  Reference: {REFERENCE_AUDIO}")
    print(f"\nSynthesis latency should be ~5s (no model reload)")
    print(f"Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
