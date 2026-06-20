#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python3
"""
Generate system voice messages using XTTS-v2 (your cloned voice).
Slower (~8s each) but uses your actual voice reference.
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

XTTS_SERVER = "http://127.0.0.1:5000"
OUT_DIR = Path("/home/openclaw/.openclaw/workspace/evez-voice/output/system-voices-cloned")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MESSAGES = {
    "startup": "System online. All services initialized. Gateway running on port 18789.",
    "health_ok": "Health check passed. All systems nominal.",
    "health_fail": "Critical alert. Service health check failed.",
    "deploy_done": "Deployment complete. All containers healthy.",
    "voice_ready": "Voice synthesis pipeline online. Ready for output.",
    "security_alert": "Security event detected. Reviewing access logs.",
    "backup_done": "Backup completed. Snapshot saved.",
    "welcome": "Welcome back. Your systems are online and operational.",
    "error": "Unhandled exception. Alert dispatched.",
    "heartbeat": "Heartbeat check. All endpoints responding.",
}

count = 0
for name, text in MESSAGES.items():
    mp3_path = OUT_DIR / f"{name}.mp3"
    wav_path = OUT_DIR / f"{name}.wav"

    try:
        payload = json.dumps({"text": text, "output": str(wav_path)}).encode()
        req = urllib.request.Request(
            f"{XTTS_SERVER}/synthesize",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        if data.get("status") == "ok":
            # The server now outputs MP3 directly (auto-converts)
            if wav_path.exists():
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path), "-ar", "44100", "-ac", "1",
                     "-b:a", "128k", str(mp3_path)],
                    capture_output=True, timeout=15
                )
                wav_path.unlink(missing_ok=True)
            elif mp3_path.exists():
                pass  # already MP3
            count += 1
            print(f"  ✅ {name}.mp3")
        else:
            print(f"  ❌ {name}: {data.get('error', 'unknown')}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

print(f"\nGenerated {count}/{len(MESSAGES)} cloned voice messages in {OUT_DIR}/")
