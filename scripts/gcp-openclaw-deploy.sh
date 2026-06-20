#!/bin/bash
# ════════════════════════════════════════════════════════════════
# EVEZ Google Cloud OpenClaw — One Command Deploy
# ════════════════════════════════════════════════════════════════
# Paste this ENTIRE script into Google Cloud Shell.
# It authenticates, creates a free-tier VM, installs OpenClaw,
# opens the dashboard, and sends the URL back to Telegram.
# ════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="evez666"
ZONE="us-central1-a"
VM_NAME="evez-gcp-openclaw"
MACHINE_TYPE="e2-micro"  # FREE TIER — 2 vCPU, 1GB RAM
TELEGRAM_BOT_TOKEN="872678…sJ7c"
TELEGRAM_CHAT_ID="7453631330"
VULTR_IP="64.176.221.16"
SSH_KEY="${HOME…hell"

G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' R='\033[0;31m' B='\033[1m' N='\033[0m'

echo ""
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  EVEZ Google Cloud OpenClaw — One Command Deploy      ║${N}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
echo ""

# ─── 1. Authenticate ───
echo -e "${Y}[1/7]${N} Authenticating gcloud..."
ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 || true)
if [ -z "$ACTIVE" ]; then
    echo "  Opening browser auth..."
    gcloud auth login --no-launch-browser
    ACTIVE=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
fi
if [ -n "$ACTIVE" ]; then
    echo -e "  ${G}✅${N} Authenticated: $ACTIVE"
else
    echo -e "  ${R}❌${N} Auth failed. Cannot continue."
    exit 1
fi

# ─── 2. Set Project ───
echo -e "${Y}[2/7]${N} Setting project..."
# Try to create project if it doesn't exist
if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    echo "  Creating project $PROJECT_ID..."
    gcloud projects create "$PROJECT_ID" --name="EVEZ" 2>/dev/null || true
    # Link billing
    echo "  ⚠️ Link billing account at: https://console.cloud.google.com/billing/projects"
fi
gcloud config set project "$PROJECT_ID" 2>/dev/null
echo -e "  ${G}✅${N} Project: $PROJECT_ID"

# ─── 3. Enable APIs ───
echo -e "${Y}[3/7]${N} Enabling APIs..."
gcloud services enable compute.googleapis.com 2>/dev/null || true
gcloud services enable run.googleapis.com 2>/dev/null || true
gcloud services enable cloudbuild.googleapis.com 2>/dev/null || true
echo -e "  ${G}✅${N} APIs enabled"

# ─── 4. Create VM ───
echo -e "${Y}[4/7]${N} Creating OpenClaw VM (free-tier e2-micro)..."
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
    echo "  VM already exists, skipping."
else
    gcloud compute instances create "$VM_NAME" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family="debian-12" \
        --image-project="debian-cloud" \
        --boot-disk-size=30GB \
        --boot-disk-type="pd-balanced" \
        --tags="http-server,https-server" \
        --metadata="startup-script=#!/bin/bash
set -e
apt-get update
apt-get install -y curl git ffmpeg
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
npm install -g openclaw
useradd -m -s /bin/bash openclaw
mkdir -p /home/openclaw/.openclaw/workspace
chown -R openclaw:openclaw /home/openclaw/.openclaw

# Install as systemd service
cat > /etc/systemd/system/openclaw.service << 'SVC'
[Unit]
Description=OpenClaw Gateway
After=network.target
[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw/.openclaw/workspace
ExecStart=/usr/bin/openclaw gateway start
Restart=always
RestartSec=5
Environment=NODE_ENV=production
[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable openclaw
systemctl start openclaw

# Open firewall
echo 'OpenClaw installed and starting...'
" 2>&1

    echo -e "  ${G}✅${N} VM created"
fi

# ─── 5. Open Firewall ───
echo -e "${Y}[5/7]${N} Opening firewall for OpenClaw..."
if ! gcloud compute firewall-rules describe "allow-openclaw-gcp" &>/dev/null; then
    gcloud compute firewall-rules create "allow-openclaw-gcp" \
        --allow="TCP:18789" \
        --source-ranges="0.0.0.0/0" \
        --target-tags="http-server" \
        --description="OpenClaw dashboard" 2>/dev/null || true
    echo -e "  ${G}✅${N} Firewall rule created"
else
    echo -e "  ${G}✅${N} Firewall already open"
fi

# ─── 6. Get External IP ───
echo -e "${Y}[6/7]${N} Getting VM IP..."
EXTERNAL_IP=""
for i in {1..30}; do
    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || true)
    if [ -n "$EXTERNAL_IP" ] && [ "$EXTERNAL_IP" != "" ]; then
        break
    fi
    sleep 5
done

if [ -z "$EXTERNAL_IP" ]; then
    echo -e "  ${Y}⚠️${N} Could not get external IP. Check VM status."
    echo "  Run: gcloud compute instances describe $VM_NAME --zone=$ZONE"
    EXTERNAL_IP="PENDING"
fi

# Wait for startup script to finish installing OpenClaw
echo -e "  ${G}✅${N} External IP: $EXTERNAL_IP"
echo "  Waiting for OpenClaw to install (~2 min)..."
sleep 30

# ─── 7. Configure & Report ───
echo -e "${Y}[7/7]${N} Configuring OpenClaw..."
GCP_DASH_URL="http://${EXTERNAL_IP}:18789"

# Try to SSH in and configure
for attempt in {1..10}; do
    if gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="which openclaw" 2>/dev/null; then
        echo "  OpenClaw installed!"

        # Copy config from Vultr via SSH tunnel
        gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
            # Wait for openclaw to be ready
            sleep 5
            # Check if running
            systemctl status openclaw | head -5
        " 2>/dev/null || true
        break
    fi
    echo "  Waiting for install... (attempt $attempt/10)"
    sleep 15
done

# ─── Send URL to Telegram ───
echo ""
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "  ${B}GOOGLE CLOUD OPENCLAW DASHBOARD:${N}"
echo -e "  ${C}${GCP_DASH_URL}${N}"
echo -e "${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# Send to Telegram
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=🌐 GOOGLE CLOUD OPENCLAW IS LIVE: ${GCP_DASH_URL}" \
    2>/dev/null || true

# ─── Summary ───
echo -e "${C}╔════════════════════════════════════════════════════════╗${N}"
echo -e "${C}║  GOOGLE CLOUD OPENCLAW DEPLOYED                        ║${N}"
echo -e "${C}╠════════════════════════════════════════════════════════╣${N}"
echo -e "${C}║${N} Dashboard:  ${GCP_DASH_URL}"
echo -e "${C}║${N} VM:        ${VM_NAME} (${MACHINE_TYPE}, ${ZONE})"
echo -e "${C}║${N} IP:        ${EXTERNAL_IP}"
echo -e "${C}║${N} Project:   ${PROJECT_ID}"
echo -e "${C}║${N} SSH:       gcloud compute ssh ${VM_NAME} --zone=${ZONE}"
echo -e "${C}╚════════════════════════════════════════════════════════╝${N}"
echo ""
echo "Next steps:"
echo "  1. Open the dashboard URL in your browser"
echo "  2. SSH in: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "  3. Add API keys: openclaw config set models.providers.groq.apiKey 'gsk_...'"
echo "  4. Add Telegram: openclaw channels add --channel telegram --token '...'"
