<p align="center">
  <img src="https://img.shields.io/badge/EVEZ-AI_Infrastructure-0f0f23?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iI2ZmZmZmZiI+PHBhdGggZD0iTTEyIDJMMiA3bDEwIDUgMTAtNS0xMC01ek0yIDE3bDEwIDUgMTAtNU0yIDEybDEwIDUgMTAtNSIvPjwvc3ZnPg==&labelColor=0f0f23" alt="EVEZ" />
</p>

<h1 align="center">EVEZ Infrastructure</h1>

<p align="center">
  <strong>Self-sustaining AI infrastructure built on OpenClaw</strong><br>
  Multi-provider model routing · Cryptographic event sourcing · Spectral graph analysis · Automated operations
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Models-32-blue" alt="32 Models" />
  <img src="https://img.shields.io/badge/Providers-8-green" alt="8 Providers" />
  <img src="https://img.shields.io/badge/Fallback_Chain-19-orange" alt="19-Model Fallback" />
  <img src="https://img.shields.io/badge/Cron_Jobs-3-purple" alt="3 Cron Jobs" />
  <img src="https://img.shields.io/badge/Telegram-@Thinga1bot-26A5E4" alt="Telegram Bot" />
  <img src="https://img.shields.io/badge/License-MIT-success" alt="MIT License" />
</p>

---

## Overview

EVEZ is a production-grade AI infrastructure stack that runs autonomously on OpenClaw. It routes requests across 8 model providers through a 19-model fallback chain, maintains a cryptographic append-only ledger for all events, and uses spectral graph analysis to detect anomalies in real time. Three automated cron jobs handle backups, health checks, and provider verification — keeping the system alive without human intervention.

The stack integrates a Telegram bot ([@Thinga1bot](https://t.me/Thinga1bot)) for conversational access, SearXNG for privacy-respecting local search, and fail2ban for SSH hardening. Everything deploys to GCP with a single bootstrap script.

---

## Architecture

### Model Routing

| Provider | Models | Free Tier |
|----------|--------|-----------|
| **Vultr** | GLM-5.1-FP8, Qwen3-235B | ✓ |
| **OpenRouter** | Multi-model gateway | ✗ |
| **Groq** | Llama-3.3-70B, Mixtral, Gemma2 | ✓ |
| **HuggingFace** | Open-source models | ✓ |
| **Google Gemini** | Gemini 2.5 Pro/Flash | ✓ |
| **Cerebras** | Llama-3.3-70B (inference) | ✓ |
| **SambaNova** | DeepSeek-R1, Llama-4-Maverick | ✓ |
| **Together AI** | Llama-3.3-70B-Turbo, DeepSeek-R1 | ✓ |

The **19-model fallback chain** automatically routes to the next available provider on rate limits, timeouts, or errors — ensuring uninterrupted operation even when individual providers go down.

### Infrastructure

```
┌─────────────────────────────────────────────────┐
│                  EVEZ Stack                      │
├─────────────┬───────────────┬───────────────────┤
│  Telegram    │   SearXNG     │   fail2ban        │
│  @Thinga1bot│  Local Search │   SSH Protection  │
├─────────────┴───────────────┴───────────────────┤
│              OpenClaw Gateway                     │
├─────────────────────────────────────────────────┤
│  8 Providers  →  32 Models  →  19-Fallback Chain │
├─────────────────────────────────────────────────┤
│  EventSpine │ Spectral Topology │ Cron Automation │
│  Ledger     │ Engine            │ (3 Jobs)        │
├─────────────────────────────────────────────────┤
│                GCP e2-medium                     │
│              Debian 12 · Node 22                  │
└─────────────────────────────────────────────────┘
```

### Automated Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| **Backup** | Daily | Workspace & config snapshots |
| **Health Check** | Every 6h | Gateway uptime & model availability |
| **Provider Check** | Daily | API key validity & rate-limit status |

### Core Systems

- **EventSpine** — Append-only cryptographic ledger. Every event is hash-chained (SHA-256) with Ed25519 signatures, providing tamper-evident audit trails for all infrastructure operations.
- **Spectral Topology Engine** — Graph-theoretic anomaly detection using eigenvalue analysis. Monitors microservice dependency graphs and flags structural drift before it causes outages.

---

## Products

| Product | Price | Description |
|---------|-------|-------------|
| **Spectral Topology Engine** | $49 | Eigenvalue-based graph anomaly detection for microservice architectures |
| **EventSpine Ledger** | $49 | Cryptographic append-only event sourcing with Ed25519 signatures |
| **EVEZ Tamagotchi Builder** | $29 | Interactive HTML builder for AI-powered virtual companions |
| **Full Stack Bundle** | $99 | All three products at a 33% discount |

---

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 22
- [OpenClaw](https://openclaw.ai/) (`npm install -g openclaw`)
- At least one API key from a supported provider

### 1. Clone & Install

```bash
git clone https://github.com/your-org/evez-infrastructure.git
cd evez-infrastructure
npm install -g openclaw   # if not already installed
```

### 2. Add API Keys

Interactive mode:

```bash
bash scripts/quick-add-keys.sh
```

Or configure manually:

```bash
# Free providers — get keys from:
# Groq:      console.groq.com
# Google:    aistudio.google.com
# Cerebras:  cloud.cerebras.ai
# SambaNova: sambanova.ai

openclaw config set models.providers.groq.apiKey "gsk_xxx"
openclaw config set models.providers.google.apiKey "AIzaxxx"
openclaw config set models.providers.cerebras.apiKey "csk-xxx"
```

### 3. Start the Gateway

```bash
openclaw gateway start
```

Dashboard runs at `http://localhost:18789`.

### 4. Deploy to GCP

```bash
# Authenticate with GCP
gcloud auth login

# Bootstrap everything (VM, firewall, OpenClaw, systemd service)
bash scripts/gcp-bootstrap.sh
```

The script creates a Debian 12 `e2-medium` VM, installs Node 22 + OpenClaw, opens port 18789, and starts the gateway as a systemd service. Full output includes your dashboard URL and SSH command.

---

## Project Structure

```
.
├── AGENTS.md                  # Agent behavior & memory conventions
├── HEARTBEAT.md               # Proactive check schedule
├── IDENTITY.md                # Agent identity config
├── SOUL.md                    # Personality & values
├── TOOLS.md                   # Local tool notes (SSH, cameras, etc.)
├── USER.md                    # User profile & preferences
│
├── eventspine/                # 🔗 EventSpine Ledger
│   ├── src/
│   │   ├── index.ts           # Core ledger (hash-chaining, signatures)
│   │   └── examples.ts        # Usage examples
│   ├── dist/                  # Compiled JS output
│   ├── package.json
│   └── tsconfig.json
│
├── topology-engine/           # 🔬 Spectral Topology Engine
│   ├── topology_engine.py     # Eigenvalue analysis & graph detection
│   ├── example_microservices.py
│   ├── test_topology_engine.py
│   └── pyproject.toml
│
├── evez-tamagotchi-builder.html  # 🥚 Tamagotchi Builder (self-contained)
│
├── scripts/
│   ├── gcp-bootstrap.sh       # One-command GCP deployment
│   └── quick-add-keys.sh      # Interactive API key setup
│
├── skills/                    # Agent skills (loaded by OpenClaw)
│   ├── cron/                  # Recurring schedule engine
│   ├── docker/                # Container management
│   ├── gcp/                   # Google Cloud operations
│   ├── git/                   # Version control
│   ├── python/                # Python best practices
│   ├── ssh-essentials/        # SSH key & tunnel management
│   └── telegram/              # Telegram Bot API workflows
│
└── memory/                    # Daily memory logs
    └── 2026-06-20.md
```

---

## Configuration

EVEZ is configured through OpenClaw's config system. Key settings:

```bash
# View current config
openclaw config get

# Set model fallback order
openclaw config set models.fallback "groq,google,cerebras,sambanova,together,openrouter,vultr,huggingface"

# Set default model
openclaw config set models.default "groq/llama-3.3-70b"

# Add Telegram bot
openclaw channels add --channel telegram --token "YOUR_BOT_TOKEN"
```

---

## Security

- **fail2ban** — Automatic SSH brute-force protection (5 failures → 1h ban)
- **SearXNG** — Local metasearch engine, no tracking, no external API leaks
- **Ed25519** — All EventSpine entries are cryptographically signed
- **SHA-256** — Hash-chained ledger provides tamper evidence
- **API keys** — Stored in OpenClaw's encrypted config, never in git

---

## License

MIT © EVEZ
