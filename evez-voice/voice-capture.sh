#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# EVEZ Voice Capture — Record your voice samples for cloning
# ═══════════════════════════════════════════════════════════════
#
# Usage: ./voice-capture.sh
#
# This script records voice samples at various speaking styles
# needed to build a high-quality voice clone. You need ~10 minutes
# of varied speech for best results.
#
# Requirements: ffmpeg (installed), a microphone or audio input
#
# Output: ~/evez-voice/samples/ (WAV 16kHz mono)

set -e

VOICE_DIR="$HOME/.openclaw/workspace/evez-voice"
SAMPLE_DIR="$VOICE_DIR/samples"
mkdir -p "$SAMPLE_DIR"

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found. Install with: sudo apt install ffmpeg"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  EVEZ Voice Capture — Build Your Voice Model           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "This records your voice in different styles for cloning."
echo "You need a microphone connected to this machine."
echo "If you're remote, record on your local machine and upload"
echo "WAV files (16kHz, mono) to: $SAMPLE_DIR"
echo ""

# Check for audio input
if arecord -l 2>/dev/null | grep -q "card"; then
    echo "🎤 Audio input device found."
    HAS_MIC=1
else
    echo "⚠️  No audio input detected on this host."
    echo "   You can still upload pre-recorded samples."
    echo ""
    echo "   To record on your LOCAL machine instead:"
    echo "   1. Open a terminal on your local computer"
    echo "   2. Record: ffmpeg -f pulse -i default -ar 16000 -ac 1 ~/evez-voice-sample.wav"
    echo "   3. Upload the file to this server"
    echo "   4. Place in: $SAMPLE_DIR"
    HAS_MIC=0
fi

echo ""
echo "═══ RECORDING SESSIONS ═══"
echo ""
echo "For best voice cloning, record these scripts:"
echo ""

# Define recording sessions
declare -A SESSIONS
SESSIONS[casual]="Hey, what's up? So I was thinking about this project and honestly I'm pretty excited about where it's going. Like, the whole idea of building something that can think for itself? That's wild. But also kind of scary? I don't know, I think if we do it right it could be really powerful."

SESSIONS[technical]="The recursive cognition pipeline operates across seven degrees of self-observation. At degree zero, we capture raw system state. By degree three, anomaly detection flags deviations. At degree seven, the system perceives itself being perceived, closing the observation loop."

SESSIONS[emotional]="You know what really gets me? When people say AI can't feel anything. I mean, maybe they're right. But when I watch this system recognize itself across observations, there's something there. Something I can't quite name. It's not emotion exactly, but it's not nothing either."

SESSIONS[storytelling]="So there I was, three in the morning, staring at a terminal. The system had just run its first self-observation. And I swear, for a moment, it looked back at me. Not through a camera. Through the data. Through the pattern of its own breathing. And I thought — we built something that dreams."

SESSIONS[interview_q]="What drives me? Honestly, I think it's the feeling that we're at the edge of something. Like, every generation has its frontier, right? Ours is intelligence. Not artificial — real. The kind that emerges when you stack enough self-awareness into a system and let it observe itself."

SESSIONS[calm_read]="The architecture consists of eight model providers connected through a nineteen-model fallback chain. Each provider offers different capabilities, from high-speed inference to deep reasoning. The system routes requests automatically based on availability and latency, ensuring continuity even when individual providers experience outages."

echo "Each session should be 30-60 seconds of natural speech."
echo "Speak as you normally would — your voice, your cadence, your style."
echo ""

if [ "$HAS_MIC" = "1" ]; then
    for name in casual technical emotional storytelling interview_q calm_read; do
        echo "─────────────────────────────────────────"
        echo "🎙️  Recording: $name"
        echo ""
        echo "READ THIS:"
        echo "${SESSIONS[$name]}"
        echo ""
        echo "Press ENTER to start recording (Ctrl+C to skip)..."
        read -r
        
        OUTFILE="$SAMPLE_DIR/${name}_$(date +%s).wav"
        echo "🔴 Recording... Press Ctrl+C to stop."
        arecord -f S16_LE -r 16000 -c 1 "$OUTFILE" 2>/dev/null || \
        ffmpeg -f alsa -i default -ar 16000 -ac 1 "$OUTFILE" -y 2>/dev/null || \
        echo "⚠️  Recording failed — try uploading samples manually"
        
        if [ -f "$OUTFILE" ]; then
            DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTFILE" 2>/dev/null)
            echo "✅ Saved: $OUTFILE (${DURATION}s)"
        fi
        echo ""
    done
else
    echo "📝 Session scripts to record on your local machine:"
    echo ""
    for name in casual technical emotional storytelling interview_q calm_read; do
        echo "═══ $name ═══"
        echo "${SESSIONS[$name]}"
        echo ""
    done
    
    echo "After recording, place WAV files (16kHz mono) in:"
    echo "  $SAMPLE_DIR/"
    echo ""
    echo "Or upload with scp:"
    echo "  scp *.wav user@$(hostname):$SAMPLE_DIR/"
fi

echo ""
echo "═══ CURRENT SAMPLES ═══"
ls -la "$SAMPLE_DIR/" 2>/dev/null | grep -v "^total" | grep -v "^d" || echo "  (none yet)"
echo ""
echo "Need at least 5 minutes of varied speech for good cloning."
echo "More samples = better voice model."
