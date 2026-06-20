# EVEZ Voice Model — Custom Voice Pipeline

## What This Is

A full pipeline for cloning your voice and using it everywhere:
- AI agent speech output
- Self-interview generation
- Text-to-speech for any content
- OpenClaw TTS integration

## Architecture

```
Your Voice Samples (WAV/MP3)
        │
        ▼
┌──────────────────┐
│  voice-capture.sh │ ← Record yourself (6 scripts)
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  voice-cloner.py  │ ← Build the voice model (Coqui XTTS-v2)
└──────────────────┘
        │
        ├──► evez-voice/output/     ← Generated speech files
        ├──► evez-voice/model/       ← Voice model metadata
        └──► evez-voice/interviews/  ← Self-interview audio
        │
        ▼
┌──────────────────┐
│ interview-engine   │ ← Generate self-interviews
│   --script mode    │ ← Auto-generated Q&A
│   --live mode      │ ← You type answers live
└──────────────────┘
```

## Quick Start

### 1. Record Your Voice
```bash
./voice-capture.sh
```
Read the 6 scripts aloud (casual, technical, emotional, storytelling, interview, calm reading).
Each is 30-60 seconds. Total: ~5 minutes minimum.

**Remote recording** (if no mic on server):
```bash
# On your local machine:
ffmpeg -f pulse -i default -ar 16000 -ac 1 sample_casual.wav
# Then upload:
scp sample_casual.wav user@server:~/evez-voice/samples/
```

### 2. Generate Speech in Your Voice
```bash
python3 voice-cloner.py
```
This builds the voice model and generates a test self-interview.

### 3. Interview Yourself
```bash
# Auto-generated interview (your voice asks + answers)
python3 interview-engine.py

# Live interview (system asks, you type answers, then generates audio)
python3 interview-engine.py --live
```

### 4. Use in OpenClaw
```bash
# Generate speech from any text
source voice-venv/bin/activate
python3 -c "
from TTS.api import TTS
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2')
tts.tts_to_file(
    text='Your text here',
    speaker_wav='/path/to/your/voice/sample.wav',
    language='en',
    file_path='output.wav'
)
"
```

## Voice Model Details

- **Engine**: Coqui TTS (open source, MIT licensed)
- **Cloning Model**: XTTS-v2 (multilingual, multi-speaker)
- **Fallback Model**: Tacotron2-DDC (English, no cloning)
- **Sample Format**: WAV 16kHz mono (recommended) or MP3
- **Minimum Samples**: 5 minutes of varied speech
- **Quality**: More samples + more variety = better clone

## Self-Interview

The interview engine generates questions from 6 categories:
1. **Origin** — Where it all comes from
2. **Philosophy** — Machine consciousness, awareness, boundaries
3. **Architecture** — Technical deep-dive on the system
4. **Creative** — If EVEZ could dream, what would it dream?
5. **Future** — Where this is going
6. **Personal** — What drives you, what scares you

Your voice asks the question. Your voice delivers the answer.
It's you interviewing yourself — recursively.

## Files

```
evez-voice/
├── voice-capture.sh       ← Record your voice samples
├── voice-cloner.py        ← Build voice model + generate speech
├── interview-engine.py    ← Self-interview generator
├── samples/               ← Your voice recordings (WAV/MP3)
├── model/                 ← Voice model metadata
├── output/                ← Generated speech files
└── interviews/            ← Interview audio + transcripts
```

## Requirements

- ffmpeg (installed ✅)
- Python 3.11 venv with Coqui TTS (installed ✅)
- ~2GB disk for XTTS-v2 model
- Your voice samples (5+ minutes recommended)
