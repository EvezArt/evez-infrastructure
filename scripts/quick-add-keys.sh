#!/bin/bash
# Quick-add API keys — paste your keys below and run: bash quick-add-keys.sh

echo "Adding API keys to OpenClaw..."

# Groq (free: console.groq.com)
read -p "Groq API key (or press Enter to skip): " GROQ_KEY
[ -n "$GROQ_KEY" ] && openclaw config set models.providers.groq.apiKey "$GROQ_KEY"

# Google Gemini (free: aistudio.google.com)
read -p "Google Gemini API key (or press Enter to skip): " GOOGLE_KEY
[ -n "$GOOGLE_KEY" ] && openclaw config set models.providers.google.apiKey "$GOOGLE_KEY"

# OpenRouter (openrouter.ai)
read -p "OpenRouter API key (or press Enter to skip): " OR_KEY
[ -n "$OR_KEY" ] && openclaw config set models.providers.openrouter.apiKey "$OR_KEY"

# Cerebras (free: cloud.cerebras.ai)
read -p "Cerebras API key (or press Enter to skip): " CEREBRAS_KEY
[ -n "$CEREBRAS_KEY" ] && openclaw config set models.providers.cerebras.apiKey "$CEREBRAS_KEY"

# SambaNova (free: sambanova.ai)
read -p "SambaNova API key (or press Enter to skip): " SAMBA_KEY
[ -n "$SAMBA_KEY" ] && openclaw config set models.providers.sambanova.apiKey "$SAMBA_KEY"

# Together AI (free $5: api.together.ai)
read -p "Together AI API key (or press Enter to skip): " TOGETHER_KEY
if [ -n "$TOGETHER_KEY" ]; then
  openclaw config set models.providers.together.baseUrl "https://api.together.xyz/v1"
  openclaw config set models.providers.together.auth "token"
  openclaw config set models.providers.together.api "openai-completions"
  openclaw config set models.providers.together.apiKey "$TOGETHER_KEY"
  openclaw config set models.providers.together.models '[
    {"id":"meta-llama/Llama-3.3-70B-Instruct-Turbo","name":"Llama-3.3-70B-Together","contextWindow":131072,"maxTokens":8192,"input":["text"]},
    {"id":"deepseek-ai/DEEPSEEK_R1","name":"DeepSeek-R1-Together","contextWindow":131072,"maxTokens":8192,"input":["text"],"reasoning":true}
  ]'
fi

echo ""
echo "=== DONE ==="
echo "Restart gateway to apply: openclaw gateway restart"
echo "Or I'll do it automatically."
