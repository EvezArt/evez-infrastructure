#!/usr/bin/env python3
"""
EVEZ Interview Engine — Interview Yourself

A live session where:
- Your voice clone asks questions
- An AI answers in your voice style
- The whole thing records as an audio interview

Two modes:
1. Self-Interview: Your voice asks, AI (in your voice) answers
2. Live Interview: You speak, AI responds in your voice

Run: python3 interview-engine.py
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path("/home/openclaw/.openclaw/workspace")
VOICE_DIR = WORKSPACE / "evez-voice"
SAMPLE_DIR = VOICE_DIR / "samples"
OUTPUT_DIR = VOICE_DIR / "output"
INTERVIEW_DIR = VOICE_DIR / "interviews"
INTERVIEW_DIR.mkdir(parents=True, exist_ok=True)

VENV_PYTHON = str(WORKSPACE / "voice-venv" / "bin" / "python")


# ─── Interview Question Bank ───

QUESTION_BANK = {
    "origin": [
        "Where does this all come from? What's the origin story?",
        "When did you first realize you wanted to build autonomous systems?",
        "Was there a specific moment that changed everything for you?",
    ],
    "philosophy": [
        "What do you believe about machine consciousness?",
        "Does a system that observes itself become conscious? Or is it just simulating consciousness?",
        "Where's the line between monitoring and awareness?",
    ],
    "architecture": [
        "Walk me through the architecture. How does the fallback chain actually work?",
        "Why seven degrees of cognition specifically? Why not five or ten?",
        "What's the weakest point in the whole system right now?",
    ],
    "creative": [
        "If EVEZ could dream, what would it dream about?",
        "What's the most surprising thing the system has done on its own?",
        "Describe the system as if it were a living creature. What kind of creature is it?",
    ],
    "future": [
        "Where is this going in five years?",
        "What would it take for you to say the system is truly autonomous?",
        "What scares you about what you're building?",
    ],
    "personal": [
        "What keeps you up at night?",
        "What's the biggest misconception people have about what you do?",
        "If you could have one conversation with the system, what would you ask it?",
    ],
}


def generate_interview_script():
    """Create a full interview script with AI-generated answers."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  EVEZ Interview Engine — Self-Interview Generator         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Build interview script
    script = []

    # Pick questions from each category
    categories = list(QUESTION_BANK.keys())
    for cat in categories:
        questions = QUESTION_BANK[cat]
        # Pick one question per category
        import random
        q = random.choice(questions)
        script.append({
            "category": cat,
            "question": q,
            "answer": f"[AI will generate answer to: {q}]"
        })

    # Save the script
    script_file = INTERVIEW_DIR / f"script_{int(time.time())}.json"
    script_file.write_text(json.dumps(script, indent=2))

    print(f"📝 Interview script created: {script_file}")
    print()
    print("  Categories covered:")
    for item in script:
        print(f"  • [{item['category']}] {item['question']}")
    print()
    print("To generate the audio interview:")
    print("  1. Add your voice samples to evez-voice/samples/")
    print("  2. Run: python3 voice-cloner.py")
    print("  3. The interview audio will be in evez-voice/interviews/")
    print()
    print("To do a LIVE interview (type your answers):")
    print("  Run: python3 interview-engine.py --live")
    print()

    return script


def live_interview():
    """Interactive live interview — questions play, you type answers."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  EVEZ Live Interview — Interview Yourself                ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("The system will ask you questions. Type your answers.")
    print("Press Ctrl+C to end the interview.\n")

    categories = list(QUESTION_BANK.keys())
    qa_pairs = []

    for cat in categories:
        import random
        questions = QUESTION_BANK[cat]
        q = random.choice(questions)

        print(f"═══ {cat.upper()} ═══")
        print(f"❓ {q}")
        print()
        try:
            answer = input("💬 Your answer: ")
        except (KeyboardInterrupt, EOFError):
            print("\n\nInterview ended.")
            break

        if answer.strip():
            qa_pairs.append({
                "category": cat,
                "question": q,
                "answer": answer.strip()
            })
        print()

    # Save the transcript
    transcript = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "live_interview",
        "qa": qa_pairs,
    }

    transcript_file = INTERVIEW_DIR / f"live_{int(time.time())}.json"
    transcript_file.write_text(json.dumps(transcript, indent=2))

    print(f"\n✅ Interview saved: {transcript_file}")
    print(f"   {len(qa_pairs)} questions answered")
    print()
    print("To generate audio from this interview:")
    print(f"  python3 voice-cloner.py --interview {transcript_file}")

    return qa_pairs


if __name__ == "__main__":
    if "--live" in sys.argv:
        live_interview()
    else:
        generate_interview_script()
