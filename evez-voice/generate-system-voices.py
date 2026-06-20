#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python3
"""
Generate system voice messages using Piper TTS.
Outputs MP3 files for each system event type.
"""
import subprocess
import os
from pathlib import Path

PIPER_MODEL = "/home/openclaw/.openclaw/workspace/evez-voice/piper-models/en_US-joe-medium.onnx"
PIPER_BIN = "/home/openclaw/.openclaw/workspace/voice-venv/bin/piper"
OUT_DIR = Path("/home/openclaw/.openclaw/workspace/evez-voice/output/system-voices")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MESSAGES = {
    "startup": "System online. All services initialized. Gateway running on port 18789.",
    "health_ok": "Health check passed. All systems nominal. CPU, memory, and disk within thresholds.",
    "health_warn": "Warning. System resources approaching threshold. Check disk usage and memory allocation.",
    "health_fail": "Critical alert. Service health check failed. Immediate attention required.",
    "deploy_start": "Deployment initiated. Building containers and pushing to registry.",
    "deploy_done": "Deployment complete. All containers healthy. Traffic routing updated.",
    "deploy_fail": "Deployment failed. Rolling back to previous stable version.",
    "git_push": "Code pushed to main branch. CI pipeline triggered.",
    "git_merge": "Pull request merged. Running integration tests before deploy.",
    "cron_run": "Scheduled task executed. Results logged. Next run queued.",
    "model_online": "Model provider responded. Latency within acceptable range.",
    "model_offline": "Model provider unreachable. Fallback engaged.",
    "voice_ready": "Voice synthesis pipeline online. XTTS server loaded. Piper standing by.",
    "voice_fail": "Voice synthesis failed. Falling back to alternate TTS engine.",
    "security_alert": "Security event detected. Reviewing access logs.",
    "backup_done": "Backup completed. Snapshot saved. Retention policy applied.",
    "backup_fail": "Backup failed. Storage target unreachable.",
    "revenue": "Revenue event recorded. Dashboard updated.",
    "heartbeat": "Heartbeat check. All endpoints responding. No anomalies.",
    "error": "Unhandled exception. Stack trace captured. Alert dispatched.",
    "welcome": "Welcome back. Your systems are online and operational.",
    "goodnight": "Entering low power mode. Heartbeat monitoring active.",
    "new_device": "New device pairing request detected. Awaiting approval.",
    "build_pass": "Build passed. All tests green. Ready for deployment.",
    "build_fail": "Build failed. Test suite returned errors. Review required.",
    "scale_up": "Auto scaling triggered. Additional capacity provisioned.",
    "scale_down": "Scaling in. Resources released. Cost optimized.",
    "payment": "Payment processed. Invoice generated. Receipt available.",
    "api_limit": "API rate limit approaching. Throttling requests.",
    "config_change": "Configuration change detected. Hot reload applied.",
}

count = 0
for name, text in MESSAGES.items():
    wav_path = OUT_DIR / f"{name}.wav"
    mp3_path = OUT_DIR / f"{name}.mp3"

    # Generate with Piper
    proc = subprocess.run(
        [PIPER_BIN, "-m", PIPER_MODEL, "-f", str(wav_path)],
        input=text, capture_output=True, text=True, timeout=30
    )

    if proc.returncode != 0:
        print(f"  ❌ {name}: Piper failed")
        continue

    # Convert to MP3
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-ar", "44100", "-ac", "1", "-b:a", "128k", str(mp3_path)],
        capture_output=True, timeout=15
    )

    # Clean up WAV
    wav_path.unlink(missing_ok=True)

    if mp3_path.exists():
        count += 1
        size = mp3_path.stat().st_size
        print(f"  ✅ {name}.mp3 ({size//1024}KB)")

print(f"\nGenerated {count}/{len(MESSAGES)} system voice messages in {OUT_DIR}/")
