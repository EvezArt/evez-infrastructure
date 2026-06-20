#!/bin/bash
# ============================================================
# EVEZ Cloud Shell Auto-Connect & Dashboard Launcher
# ============================================================
# Run this in Google Cloud Shell to automatically:
# 1. Authenticate gcloud (if needed)
# 2. SSH tunnel to your Vultr OpenClaw gateway
# 3. Open the dashboard with token auth
# 4. Set up persistent background connection
# ============================================================

set -euo pipefail

# ─── Config ───
GATEWAY_HOST="5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com"
GATEWAY_PORT="18789"
GATEWAY_TOKEN="W7aVCahxCxD5ZhL5OJ2k82HTXO07BxB0"
GCP_PROJECT="evez666"
VULTR_IP="64.176.221.16"
SSH_KEY="${HOME}/.ssh/id_evez_gateway"

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  EVEZ Cloud Shell — Auto-Connect & Dashboard    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─── 1. Check gcloud auth ───
echo -e "${YELLOW}[1/5]${NC} Checking gcloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q @; then
    echo "  No active gcloud account. Launching auth..."
    gcloud auth login --no-launch-browser
fi

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
if [ -n "$ACTIVE_ACCOUNT" ]; then
    echo -e "  ${GREEN}✅${NC} Authenticated as: $ACTIVE_ACCOUNT"
else
    echo -e "  ${RED}❌${NC} No gcloud account. Run: gcloud auth login --no-launch-browser"
    exit 1
fi

# ─── 2. Set project ───
echo -e "${YELLOW}[2/5]${NC} Setting GCP project..."
gcloud config set project "$GCP_PROJECT" 2>/dev/null
echo -e "  ${GREEN}✅${NC} Project: $GCP_PROJECT"

# ─── 3. SSH tunnel to Vultr gateway ───
echo -e "${YELLOW}[3/5]${NC} Setting up SSH tunnel to Vultr gateway..."

# Generate SSH key if missing
if [ ! -f "$SSH_KEY" ]; then
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "evez-cloud-shell" 2>/dev/null
    echo "  Generated SSH key: $SSH_KEY"
fi

# Kill any existing tunnel on our port
pkill -f "ssh.*-f.*$GATEWAY_PORT:127.0.0.1:$GATEWAY_PORT" 2>/dev/null || true

# Try direct tunnel (works if SSH is open on Vultr)
# Fall back to just using the public domain
if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes root@"$VULTR_IP" exit 2>/dev/null; then
    echo "  SSH to Vultr available, establishing tunnel..."
    ssh -f -N -L "${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        root@"$VULTR_IP"
    DASHBOARD_URL="http://127.0.0.1:${GATEWAY_PORT}"
    echo -e "  ${GREEN}✅${NC} SSH tunnel active → localhost:${GATEWAY_PORT}"
else
    echo "  Direct SSH not available, using public domain..."
    DASHBOARD_URL="https://${GATEWAY_HOST}"
    echo -e "  ${YELLOW}⚠️${NC} Using public URL (no tunnel)"
fi

# ─── 4. Open dashboard ───
echo -e "${YELLOW}[4/5]${NC} Launching dashboard..."

# Write the dashboard URL with token for easy access
AUTH_URL="${DASHBOARD_URL}?token=${GATEWAY_TOKEN}"
echo ""
echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${CYAN}Dashboard:${NC} ${AUTH_URL}"
echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Try to open in browser (Cloud Shell web preview)
if command -v webpreview 2>/dev/null; then
    webpreview "$GATEWAY_PORT"
elif [ -n "${CLOUD_SHELL:-}" ]; then
    echo "  Cloud Shell detected. Click 'Web Preview' → port $GATEWAY_PORT"
fi

# ─── 5. Set up persistent connection ───
echo -e "${YELLOW}[5/5]${NC} Setting up persistent connection..."

# Create an autostart script
AUTOSTART_DIR="${HOME}/.config/cloudshell"
AUTOSTART_FILE="${AUTOSTART_DIR}/evez-connect.sh"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_FILE" << 'AUTOSTART'
#!/bin/bash
# EVEZ Auto-Connect — runs on Cloud Shell startup
GATEWAY_HOST="5e8b5d27-3fe0-4890-9a85-513cafb28ea1.vultropenclaw.com"
GATEWAY_PORT="18789"
GATEWAY_TOKEN="W7aVCahxCxD5ZhL5OJ2k82HTXO07BxB0"
VULTR_IP="64.176.221.16"

# Establish SSH tunnel if possible
pkill -f "ssh.*-f.*${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" 2>/dev/null || true
if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes root@"$VULTR_IP" exit 2>/dev/null; then
    ssh -f -N -L "${GATEWAY_PORT}:127.0.0.1:${GATEWAY_PORT}" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        root@"$VULTR_IP" 2>/dev/null
fi

echo "EVEZ Dashboard: http://127.0.0.1:${GATEWAY_PORT}?token=${GATEWAY_TOKEN}"
AUTOSTART

chmod +x "$AUTOSTART_FILE"

# Add to .bashrc if not already there
if ! grep -q "evez-connect" "${HOME}/.bashrc" 2>/dev/null; then
    echo "" >> "${HOME}/.bashrc"
    echo "# EVEZ Auto-Connect" >> "${HOME}/.bashrc"
    echo "if [ -f '${AUTOSTART_FILE}' ]; then '${AUTOSTART_FILE}'; fi" >> "${HOME}/.bashrc"
fi

echo -e "  ${GREEN}✅${NC} Auto-connect installed in ~/.bashrc"
echo ""

# ─── Summary ───
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  SETUP COMPLETE                                  ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC} Dashboard:  ${AUTH_URL}"
echo -e "${CYAN}║${NC} Gateway:    ${GATEWAY_HOST}:${GATEWAY_PORT}"
echo -e "${CYAN}║${NC} Vultr IP:   ${VULTR_IP}"
echo -e "${CYAN}║${NC} Auto-start: ${AUTOSTART_FILE}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "Every time you open Cloud Shell, the tunnel auto-connects."
echo "Bookmark the dashboard URL for one-click access."
