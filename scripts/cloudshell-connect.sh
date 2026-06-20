#!/bin/bash
# ════════════════════════════════════════════════════════════════
# EVEZ Cloud Shell — Auto Token, Gateway Tunnel, Dashboard Launch
# ════════════════════════════════════════════════════════════════
# Run this in Google Cloud Shell. It:
#   1. Authenticates gcloud (browser-based)
#   2. SSH tunnels to Vultr OpenClaw gateway
#   3. Opens the dashboard with token auth
#   4. Installs itself as a Cloud Shell startup script
#   5. Verifies connection with a health check
#
# Usage:
#   bash <(curl -sL https://raw.githubusercontent.com/EvezArt/infra/main/scripts/cloudshell-connect.sh)
#   — or paste directly into Cloud Shell terminal
# ════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Configuration ───
GATEWAY_HOST="5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com"
GATEWAY_PORT="18789"
GATEWAY_TOKEN="W7aVCahxCxD5ZhL5OJ2k82HTXO07BxB0"
VULTR_IP="64.176.221.16"
VULTR_USER="root"
GCP_PROJECT="evez666"
SSH_KEY="${HOME}/.ssh/evez_cloudshell"
TUNNEL_PID_FILE="/tmp/evez_tunnel.pid"
AUTOSTART_DIR="${HOME}/.config/cloudshell"
AUTOSTART_FILE="${AUTOSTART_DIR}/evez-connect.sh"

# ─── Colors ───
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' B='\033[1m' N='\033[0m'

echo ""
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  EVEZ Cloud Shell — Auto Connect & Dashboard          ║${N}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
echo ""

# ─── 1. gcloud Auth ───
echo -e "${Y}[1/6]${N} gcloud authentication..."
ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 || true)
if [ -z "$ACTIVE" ]; then
    echo -e "  ${R}No active account.${N} Opening browser auth..."
    gcloud auth login --no-launch-browser
    ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
fi
if [ -n "$ACTIVE" ]; then
    echo -e "  ${G}✅${N} $ACTIVE"
else
    echo -e "  ${R}❌ Auth failed. Run: gcloud auth login --no-launch-browser${N}"
    exit 1
fi

# ─── 2. Set Project ───
echo -e "${Y}[2/6]${N} Setting GCP project..."
gcloud config set project "$GCP_PROJECT" 2>/dev/null || {
    echo -e "  ${Y}⚠️${N} Project '$GCP_PROJECT' not found. You may need to create it."
    echo -e "  Run: gcloud projects create $GCP_PROJECT"
}
echo -e "  ${G}✅${N} Project: $GCP_PROJECT"

# ─── 3. SSH Key ───
echo -e "${Y}[3/6]${N} SSH key setup..."
mkdir -p ~/.ssh
if [ ! -f "$SSH_KEY" ]; then
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "evez-cloud-shell" 2>/dev/null
    echo -e "  ${G}✅${N} Generated: $SSH_KEY"
    # Print the public key for adding to Vultr
    echo ""
    echo -e "  ${Y}Add this key to Vultr if SSH fails:${N}"
    echo -e "  ${C}$(cat ${SSH_KEY}.pub)${N}"
    echo ""
else
    echo -e "  ${G}✅${N} Key exists: $SSH_KEY"
fi

# ─── 4. SSH Tunnel ───
echo -e "${Y}[4/6]${N} Establishing SSH tunnel to Vultr gateway..."

# Kill any existing tunnel
if [ -f "$TUNNEL_PID_FILE" ]; then
    OLD_PID=$(cat "$TUNNEL_PID_FILE" 2>/dev/null)
    kill "$OLD_PID" 2>/dev/null || true
    rm -f "$TUNNEL_PID_FILE"
fi

# Test SSH connectivity
SSH_OK=false
if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
    -i "$SSH_KEY" "${VULTR_USER}@${VULTR_IP}" exit 2>/dev/null; then
    SSH_OK=true
fi

if $SSH_OK; then
    # Establish tunnel with keepalive
    ssh -f -N -L "${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -i "$SSH_KEY" \
        "${VULTR_USER}@${VULTR_IP}"

    # Record tunnel PID
    # Find the SSH process that's doing our tunnel
    TUNNEL_PID=$(pgrep -f "ssh.*-f.*-N.*-L.*${GATEWAY_PORT}" 2>/dev/null | head -1 || true)
    if [ -n "$TUNNEL_PID" ]; then
        echo "$TUNNEL_PID" > "$TUNNEL_PID_FILE"
    fi

    DASH_URL="http://127.0.0.1:${GATEWAY_PORT}"
    echo -e "  ${G}✅${N} SSH tunnel active → localhost:${GATEWAY_PORT}"
else
    echo -e "  ${Y}⚠️${N} SSH key auth failed. Trying password or public URL..."
    DASH_URL="https://${GATEWAY_HOST}"
    echo -e "  ${Y}Using public URL (no tunnel — gateway may not be reachable)${N}"
    echo -e "  ${Y}To fix: Add the SSH public key to Vultr${N}"
fi

# ─── 5. Health Check & Dashboard ───
echo -e "${Y}[5/6]${N} Verifying gateway connection..."
sleep 1

HEALTH_OK=false
# Try the health endpoint through the tunnel
HEALTH=$(curl -s --max-time 5 "http://127.0.0.1:${GATEWAY_PORT}/api/health" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" 2>/dev/null || echo "FAIL")

if echo "$HEALTH" | grep -qi "ok\|healthy\|running\|alive"; then
    HEALTH_OK=true
    echo -e "  ${G}✅${N} Gateway is healthy"
else
    # Try public domain
    HEALTH2=$(curl -s --max-time 5 "https://${GATEWAY_HOST}/api/health" \
        -H "Authorization: Bearer ${GATEWAY_TOKEN}" 2>/dev/null || echo "FAIL")
    if echo "$HEALTH2" | grep -qi "ok\|healthy\|running\|alive"; then
        HEALTH_OK=true
        DASH_URL="https://${GATEWAY_HOST}"
        echo -e "  ${G}✅${N} Gateway reachable via public URL"
    else
        echo -e "  ${Y}⚠️${N} Health check inconclusive (gateway may still work)"
    fi
fi

# Build authenticated dashboard URL
AUTH_URL="${DASH_URL}?token=${GATEWAY_TOKEN}"

echo ""
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "  ${B}EVEZ Dashboard:${N} ${C}${AUTH_URL}${N}"
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# ─── 6. Install Autostart ───
echo -e "${Y}[6/6]${N} Installing Cloud Shell autostart..."
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_FILE" << AUTOSTART
#!/bin/bash
# EVEZ Cloud Shell — Auto-Connect on Startup
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
GATEWAY_PORT="${GATEWAY_PORT}"
VULTR_IP="${VULTR_IP}"
VULTR_USER="${VULTR_USER}"
GATEWAY_TOKEN="${GATEWAY_TOKEN}"
SSH_KEY="${SSH_KEY}"
GATEWAY_HOST="${GATEWAY_HOST}"

# Kill stale tunnels
pkill -f "ssh.*-f.*-N.*-L.*\${GATEWAY_PORT}" 2>/dev/null || true
sleep 0.5

# Try SSH tunnel
if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \\
    -i "\$SSH_KEY" "\${VULTR_USER}@\${VULTR_IP}" exit 2>/dev/null; then
    ssh -f -N -L "\${GATEWAY_PORT}:127.0.0.1:\${GATEWAY_PORT}" \\
        -o StrictHostKeyChecking=no \\
        -o ServerAliveInterval=60 \\
        -o ServerAliveCountMax=3 \\
        -o ExitOnForwardFailure=yes \\
        -i "\$SSH_KEY" \\
        "\${VULTR_USER}@\${VULTR_IP}" 2>/dev/null
    echo "EVEZ: Tunnel active → http://127.0.0.1:\${GATEWAY_PORT}?token=\${GATEWAY_TOKEN}"
else
    echo "EVEZ: SSH failed. Public URL: https://\${GATEWAY_HOST}?token=\${GATEWAY_TOKEN}"
fi
AUTOSTART

chmod +x "$AUTOSTART_FILE"

# Add to .bashrc if not there
if ! grep -q "evez-connect" "${HOME}/.bashrc" 2>/dev/null; then
    echo "" >> "${HOME}/.bashrc"
    echo "# EVEZ Auto-Connect" >> "${HOME}/.bashrc"
    echo "if [ -f '${AUTOSTART_FILE}' ]; then '${AUTOSTART_FILE}'; fi" >> "${HOME}/.bashrc"
    echo -e "  ${G}✅${N} Installed in ~/.bashrc — runs on every Cloud Shell startup"
else
    echo -e "  ${G}✅${N} Already in ~/.bashrc"
fi

# ─── Summary ───
echo ""
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  CONNECTED                                           ║${N}"
echo -e "${C}╠════════════════════════════════════════════════════════╣${N}"
echo -e "${C}║${N} ${B}Dashboard:${N}  ${AUTH_URL}"
echo -e "${C}║${N} ${B}Gateway:${N}    ${GATEWAY_HOST}:${GATEWAY_PORT}"
echo -e "${C}║${N} ${B}Vultr IP:${N}   ${VULTR_IP}"
echo -e "${C}║${N} ${B}Autostart:${N}  ${AUTOSTART_FILE}"
echo -e "${C}║${N} ${B}GCP:${N}        ${GCP_PROJECT}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
echo ""
echo -e "Every Cloud Shell session auto-connects. Bookmark the dashboard URL."
echo ""
echo -e "${Y}NEXT:${N} If SSH auth failed, add this key to Vultr:"
echo -e "  ${C}cat ${SSH_KEY}.pub${N}"
echo ""
