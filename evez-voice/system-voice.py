#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python3
"""
EVEZ System Voice — Play pre-generated system audio notifications.
Use from cron, scripts, or OpenClaw to deliver voiced system events.

Usage:
  python3 system-voice.py <event_name>
  python3 system-voice.py startup
  python3 system-voice.py health_fail
  python3 system-voice.py deploy_done

Events: startup, health_ok, health_warn, health_fail, deploy_start,
  deploy_done, deploy_fail, git_push, git_merge, cron_run, model_online,
  model_offline, voice_ready, voice_fail, security_alert, backup_done,
  backup_fail, revenue, heartbeat, error, welcome, goodnight,
  new_device, build_pass, build_fail, scale_up, scale_down,
  payment, api_limit, config_change
"""
import sys
import json
import os
import urllib.request
from pathlib import Path

VOICE_DIR = Path("/home/openclaw/.openclaw/workspace/evez-voice/output")
SYSTEM_DIR = VOICE_DIR / "system-voices"
CLONED_DIR = VOICE_DIR / "system-voices-cloned"
BOT_TOKEN_FILE = "/home/openclaw/.openclaw/openclaw.json"
OWNER_ID = "7453631330"

def get_bot_token():
    with open(BOT_TOKEN_FILE) as f:
        cfg = json.load(f)
    return cfg["channels"]["telegram"]["botToken"]

def send_voice_note(chat_id, audio_path, bot_token):
    """Send a voice note via Telegram Bot API."""
    import subprocess
    curl_cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{bot_token}/sendVoice",
        "-F", f"chat_id={chat_id}",
        "-F", f"voice=@{audio_path}",
    ]
    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

def main():
    if len(sys.argv) < 2:
        print("Usage: system-voice.py <event_name>")
        print(f"Available: {', '.join(sorted(p.stem for p in SYSTEM_DIR.glob('*.mp3')))}")
        sys.exit(1)

    event = sys.argv[1]

    # Try cloned voice first, fall back to Piper
    audio_path = CLONED_DIR / f"{event}.mp3"
    source = "cloned"

    if not audio_path.exists():
        audio_path = SYSTEM_DIR / f"{event}.mp3"
        source = "piper"

    if not audio_path.exists():
        print(f"Unknown event: {event}")
        print(f"Available: {', '.join(sorted(p.stem for p in SYSTEM_DIR.glob('*.mp3')))}")
        sys.exit(1)

    # Send via Telegram
    bot_token = get_bot_token()
    ok = send_voice_note(OWNER_ID, str(audio_path), bot_token)
    if ok:
        print(f"✅ Sent {event} ({source})")
    else:
        print(f"❌ Failed to send {event}")

if __name__ == "__main__":
    main()
