#!/home/openclaw/.openclaw/workspace/voice-venv/bin/python3
"""
EVEZ Strategy Accumulator — Long-term self-sustaining strategic memory.

Reads from:
  - MEMORY.md (curated long-term memory)
  - memory/*.md (daily notes)
  - evez-voice/ (voice pipeline state)
  - skills/ (accumulated capabilities)
  - OpenClaw config (system state)

Outputs:
  - strategy/current.md — Active strategy document
  - strategy/capabilities.md — What EVEZ can do right now
  - strategy/next-moves.md — Prioritized action queue

Run periodically via cron or heartbeat.
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/openclaw/.openclaw/workspace")
STRATEGY_DIR = WORKSPACE / "strategy"
STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

def get_system_state():
    """Gather current system capabilities."""
    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": [],
        "channels": [],
        "skills": [],
        "voice": "unknown",
        "nodes": [],
    }

    # Count models from config
    config_path = Path("/home/openclaw/.openclaw/openclaw.json")
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text())
            providers = cfg.get("models", {}).get("providers", {})
            total_models = 0
            for pname, prov in providers.items():
                models = prov.get("models", [])
                total_models += len(models)
            state["models"] = total_models
            state["channels"] = list(cfg.get("channels", {}).keys())
        except Exception:
            pass

    # Check voice pipeline
    synth = WORKSPACE / "evez-voice" / "evez-voice-synth.py"
    if synth.exists():
        content = synth.read_text()
        if "edge_tts" in content:
            state["voice"] = "edge-tts (BrianNeural, ~2s latency)"
        elif "xtts" in content.lower():
            state["voice"] = "xtts-v2 (cloned, ~25s latency)"

    # Count skills
    skills_dir = WORKSPACE / "skills"
    if skills_dir.exists():
        state["skills"] = [d.name for d in skills_dir.iterdir() if d.is_dir()]

    # Count voice samples
    samples_dir = WORKSPACE / "evez-voice" / "samples"
    if samples_dir.exists():
        state["voice_samples"] = len(list(samples_dir.glob("*.*")))

    # Disk and memory
    try:
        df = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        state["disk"] = df.stdout.strip().split("\n")[-1] if df.returncode == 0 else "unknown"
    except Exception:
        pass

    try:
        free = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        lines = free.stdout.strip().split("\n")
        state["memory"] = lines[1] if len(lines) > 1 else "unknown"
    except Exception:
        pass

    return state

def get_recent_memory():
    """Read recent daily memory files."""
    memory_dir = WORKSPACE / "memory"
    notes = {}
    if memory_dir.exists():
        files = sorted(memory_dir.glob("*.md"), reverse=True)[:7]
        for f in files:
            try:
                notes[f.name] = f.read_text()[:2000]
            except Exception:
                pass
    return notes

def build_capabilities(state):
    """Build capabilities document."""
    cap = STRATEGY_DIR / "capabilities.md"
    content = f"""# EVEZ Capabilities — {state['timestamp']}

## System
- **Models**: {state.get('models', '?')} across multiple providers
- **Channels**: {', '.join(state.get('channels', []))}
- **Voice**: {state.get('voice', 'not configured')}
- **Voice Samples**: {state.get('voice_samples', 0)} collected
- **Skills**: {len(state.get('skills', []))} accumulated

## Skills Inventory
"""
    for skill in sorted(state.get("skills", [])):
        content += f"- {skill}\n"

    content += f"""
## Infrastructure
- **Host**: Vultr VPS (64.176.221.16)
- **Gateway Port**: 18789
- **Public Domain**: 5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com
- **Disk**: {state.get('disk', 'unknown')}
- **Memory**: {state.get('memory', 'unknown')}

## Cost: $0/mo
All model providers are free tier. Voice is edge-tts (free). 
Infrastructure is the only cost (Vultr VPS).
"""
    cap.write_text(content)
    return content

def build_next_moves(state):
    """Build prioritized next moves."""
    moves = STRATEGY_DIR / "next-moves.md"
    content = f"""# EVEZ Next Moves — {state['timestamp']}

## Immediate (This Session)
1. **Cloud Shell integration** — Auto-connect + dashboard auth ✅
2. **Voice pipeline** — Edge TTS active, ~2s latency ✅
3. **Strategy accumulator** — This system ✅

## Short-Term (This Week)
1. **Get gcloud authenticated** — `gcloud auth login` on Cloud Shell, then run cloudshell-setup.sh
2. **Set up SSH tunnel** — Cloud Shell → Vultr for persistent dashboard access
3. **Add more voice samples** — Record directly via Telegram voice messages
4. **Memory index rebuild** — `openclaw memory index --force` to fix search

## Medium-Term (This Month)
1. **GCP free tier VM** — Bootstrap a power node for redundancy
2. **Piper TTS local** — Fully offline voice as edge-tts fallback
3. **Revenue products** — Get Spectral Topology Engine, EventSpine, Tamagotchi Builder selling
4. **Cron heartbeat jobs** — Automated health checks, email/calendar monitoring

## Long-Term (Ongoing)
1. **Self-sustaining infrastructure** — Auto-healing, auto-scaling, zero manual intervention
2. **Voice quality** — More samples → better XTTS clone for offline use
3. **Skill accumulation** — Every solved problem becomes a reusable skill
4. **Strategic memory** — This accumulator grows smarter over time

## Revenue Targets
- Spectral Topology Engine: $49
- EventSpine: $49
- Tamagotchi Builder: $29
- Bundle: $99
"""
    moves.write_text(content)
    return content

def build_current_strategy(state, memory):
    """Build the main strategy document."""
    strat = STRATEGY_DIR / "current.md"
    content = f"""# EVEZ Strategy — {state['timestamp']}

## Mission
Build self-sustaining AI infrastructure that observes itself, 
expresses its state in human-readable signals, and generates 
revenue through three products. Zero vendor lock-in. Zero recurring cost.

## Current State
- **Live**: Vultr VPS, OpenClaw gateway, Telegram bot
- **Voice**: Edge TTS (BrianNeural) — American Western, ~2s latency
- **Models**: {state.get('models', '?')} free-tier models across providers
- **Skills**: {len(state.get('skills', []))} accumulated
- **Cost**: $0/mo (Vultr VPS only)

## Architecture
```
Telegram ←→ OpenClaw Gateway ←→ Multi-provider LLM chain
     ↓                              ↓
   Voice TTS ← edge-tts        19-model fallback
     ↓                              ↓
   Strategy ← This accumulator   Cron jobs
     ↓
   Memory ← MEMORY.md + daily notes
```

## Strategic Principles
1. **Free-first** — Every service has a free tier. Use it.
2. **Accumulate** — Every solution becomes a skill. Every skill compounds.
3. **Observe** — The system watches itself. Signals > silence.
4. **Sustain** — Zero recurring cost = infinite runway.
5. **Ship** — Revenue products fund expansion. No funding rounds needed.

## Recent Memory
"""
    for name, text in memory.items():
        content += f"\n### {name}\n{text[:500]}\n"

    strat.write_text(content)
    return content

def main():
    print("EVEZ Strategy Accumulator")
    print("=" * 40)

    state = get_system_state()
    memory = get_recent_memory()

    cap = build_capabilities(state)
    print(f"✅ capabilities.md — {len(state.get('skills', []))} skills tracked")

    moves = build_next_moves(state)
    print("✅ next-moves.md — prioritized action queue")

    strat = build_current_strategy(state, memory)
    print("✅ current.md — strategic overview updated")

    print(f"\nStrategy dir: {STRATEGY_DIR}/")

if __name__ == "__main__":
    main()
