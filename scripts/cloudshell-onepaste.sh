#!/bin/bash
# ════════════════════════════════════════════════════════════════
# EVEZ Cloud Shell — One-Paste Auto-Connect
# ════════════════════════════════════════════════════════════════
# Paste this entire script into Google Cloud Shell.
# It sets up SSH tunneling to your Vultr OpenClaw gateway,
# authenticates with the gateway token, and opens the dashboard.
# Also installs itself as a Cloud Shell startup script.
# ════════════════════════════════════════════════════════════════

set -euo pipefail

GATEWAY_PORT="18789"
GATEWAY_TOKEN="W7aVCahxCxD5ZhL5OJ2k82HTXO07BxB0"
VULTR_IP="64.176.221.16"
VULTR_USER="openclaw"
GCP_PROJECT="evez666"
GATEWAY_HOST="5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com"

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' B='\033[1m' N='\033[0m'

echo ""
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  EVEZ Cloud Shell — Auto Connect & Dashboard          ║${N}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
echo ""

# ─── 1. Install SSH key (embedded) ───
echo -e "${Y}[1/5]${N} Installing SSH key..."
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat > ~/.ssh/evez-cloudshell << 'SSHKEY'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACADsJTbjuqF6XCXkX6s9GhtEaD8UaeX+Y0kKXVoi4dPbQAAAJipFxYsqRcW
LAAAAAtzc2gtZWQyNTUxOQAAACADsJTbjuqF6XCXkX6s9GhtEaD8UaeX+Y0kKXVoi4dPbQ
AAAECZKrfZMB7T9mcBfuMIPXQxwx6kmJ2fvHqHvWIwBsLc+QOwlNuO6oXpcJeRfqz0aG0R
oPxRp5f5jSQpdWiLh09tAAAAD2V2ZXotY2xvdWRzaGVsbAECAwQFBg==
-----END OPENSSH PRIVATE KEY-----
SSHKEY
chmod 600 ~/.ssh/evez-cloudshell
echo -e "  ${G}✅${N} SSH key installed"

# ─── 2. gcloud Auth ───
echo -e "${Y}[2/5]${N} gcloud authentication..."
ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 || true)
if [ -z "$ACTIVE" ]; then
    echo "  Opening browser auth..."
    gcloud auth login --no-launch-browser
    ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
fi
if [ -n "$ACTIVE" ]; then
    echo -e "  ${G}✅${N} $ACTIVE"
    gcloud config set project "$GCP_PROJECT" 2>/dev/null || true
else
    echo -e "  ${Y}⚠️${N} gcloud auth skipped (not required for tunnel)"
fi

# ─── 3. SSH Tunnel ───
echo -e "${Y}[3/5]${N} SSH tunnel to Vultr..."
pkill -f "ssh.*-f.*-N.*-L.*${GATEWAY_PORT}" 2>/dev/null || true
sleep 0.5

TUNNEL_OK=false
for USER_TRY in openclaw root; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
        -i ~/.ssh/evez-cloudshell \
        "${USER_TRY}@${VULTR_IP}" exit 2>/dev/null; then
        VULTR_USER="$USER_TRY"
        TUNNEL_OK=true
        break
    fi
done

if $TUNNEL_OK; then
    ssh -f -N -L "${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -i ~/.ssh/evez-cloudshell \
        "${VULTR_USER}@${VULTR_IP}"
    DASH_URL="http://127.0.0.1:${GATEWAY_PORT}"
    echo -e "  ${G}✅${N} Tunnel active (${VULTR_USER}@${VULTR_IP})"
else
    DASH_URL="https://${GATEWAY_HOST}"
    echo -e "  ${Y}⚠️${N} SSH auth failed. Falling back to public URL."
fi

# ─── 4. Health Check ───
echo -e "${Y}[4/5]${N} Verifying gateway..."
sleep 1
HEALTH=$(curl -s --max-time 5 "${DASH_URL}/api/health" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" 2>/dev/null || echo "no-response")
if echo "$HEALTH" | grep -qi "ok\|health\|run\|alive"; then
    echo -e "  ${G}✅${N} Gateway healthy"
else
    echo -e "  ${Y}⚠️${N} Health check inconclusive — dashboard may still work"
fi

AUTH_URL="${DASH_URL}?token=${GATEWAY_TOKEN}"

echo ""
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "  ${B}DASHBOARD:${N} ${C}${AUTH_URL}${N}"
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# ─── 5. Install Autostart ───
echo -e "${Y}[5/5]${N} Installing autostart..."
AUTOSTART_DIR="${HOME}/.config/cloudshell"
AUTOSTART_FILE="${AUTOSTART_DIR}/evez-connect.sh"
mkdir -p "$AUTOSTART_DIR"

# Re-create autostart with embedded key
cat > "$AUTOSTART_FILE" << 'AUTOSTART'
#!/bin/bash
# EVEZ Cloud Shell — Auto-Connect
GATEWAY_PORT="18789"
GATEWAY_TOKEN="W7aVCahxCxD5ZhL5OJ2k82HTXO07BxB0"
VULTR_IP="64.176.221.16"
GATEWAY_HOST="5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com"
SSH_KEY="${HOME}/.ssh/evez-cloudshell"

pkill -f "ssh.*-f.*-N.*-L.*${GATEWAY_PORT}" 2>/dev/null || true
sleep 0.5

for USER_TRY in openclaw root; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
        -i "$SSH_KEY" "${USER_TRY}@${VULTR_IP}" exit 2>/dev/null; then
        ssh -f -N -L "${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" \
            -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=60 \
            -o ExitOnForwardFailure=yes \
            -i "$SSH_KEY" \
            "${USER_TRY}@${VULTR_IP}" 2>/dev/null
        echo "EVEZ: http://127.0.0.1:${GATEWAY_PORT}?token=${GATEWAY_TOKEN}"
        exit 0
    fi
done
echo "EVEZ: SSH failed. https://${GATEWAY_HOST}?token=${GATEWAY_TOKEN}"
AUTOSTART

chmod +x "$AUTOSTART_FILE"

if ! grep -q "evez-connect" "${HOME}/.bashrc" 2>/dev/null; then
    echo "" >> "${HOME}/.bashrc"
    echo "# EVEZ Auto-Connect" >> "${HOME}/.bashrc"
    echo "[ -f '${AUTOSTART_FILE}' ] && '${AUTOSTART_FILE}'" >> "${HOME}/.bashrc"
    echo -e "  ${G}✅${N} Autostart installed"
else
    echo -e "  ${G}✅${N} Autostart already in .bashrc"
fi

echo ""
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  DONE — Every Cloud Shell session auto-connects now    ║${N}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
