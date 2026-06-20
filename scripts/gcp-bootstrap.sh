#!/bin/bash
# ============================================================
# GCP Infrastructure Bootstrap for OpenClaw
# Run this AFTER: gcloud auth login
# Target: cheapest VM with enough RAM for multi-model routing
# ============================================================

set -euo pipefail

PROJECT_ID="evez666"
ZONE="us-central1-a"
VM_NAME="openclaw-power-node"
MACHINE_TYPE="e2-medium"  # 2 vCPU, 4GB RAM — ~$25/mo
# Cheaper option: e2-small (2 vCPU, 2GB) — ~$13/mo
# If you need more: e2-standard-2 (2 vCPU, 8GB) — ~$50/mo

echo "=== EVEZ OpenClaw GCP Bootstrap ==="
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "VM: $VM_NAME ($MACHINE_TYPE)"
echo ""

# 1. Set project
echo "[1/7] Setting project..."
gcloud config set project "$PROJECT_ID"

# 2. Create VM if it doesn't exist
echo "[2/7] Creating VM (if not exists)..."
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
apt-get update
apt-get install -y curl git
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
npm install -g openclaw
useradd -m -s /bin/bash openclaw
mkdir -p /home/openclaw/.openclaw/workspace
chown -R openclaw:openclaw /home/openclaw/.openclaw"
  echo "  VM created."
fi

# 3. Open firewall for OpenClaw dashboard
echo "[3/7] Configuring firewall..."
if ! gcloud compute firewall-rules describe "allow-openclaw" &>/dev/null; then
  gcloud compute firewall-rules create "allow-openclaw" \
    --allow="TCP:18789" \
    --source-ranges="0.0.0.0/0" \
    --target-tags="http-server" \
    --description="OpenClaw dashboard"
  echo "  Firewall rule created."
else
  echo "  Firewall rule exists."
fi

# 4. SSH in and install OpenClaw
echo "[4/7] Installing OpenClaw on VM..."
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  if command -v openclaw &>/dev/null; then
    echo 'OpenClaw already installed.'
  else
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
    sudo npm install -g openclaw
    echo 'OpenClaw installed.'
  fi
"

# 5. Copy your local config to the VM
echo "[5/7] Syncing configuration..."
LOCAL_CONFIG="$HOME/.openclaw/openclaw.json"
if [ -f "$LOCAL_CONFIG" ]; then
  gcloud compute scp "$LOCAL_CONFIG" "$VM_NAME":/home/openclaw/.openclaw/openclaw.json --zone="$ZONE" 2>/dev/null || \
    echo "  Note: SSH key may need setup. Run: gcloud compute config-ssh"
else
  echo "  No local config found, skipping."
fi

# 6. Start OpenClaw as a systemd service on the VM
echo "[6/7] Starting OpenClaw service..."
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  sudo tee /etc/systemd/system/openclaw.service > /dev/null << 'SERVICE'
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
SERVICE
  sudo systemctl daemon-reload
  sudo systemctl enable openclaw
  sudo systemctl start openclaw
  echo 'OpenClaw service started.'
"

# 7. Get the external IP
echo "[7/7] Getting access URL..."
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "UNKNOWN")
echo ""
echo "=========================================="
echo "DONE. OpenClaw should be running."
echo "Dashboard: http://$EXTERNAL_IP:18789"
echo "SSH: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. SSH in: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "2. Add API keys: openclaw config set models.providers.groq.apiKey 'gsk_xxx'"
echo "3. Add Telegram: openclaw channels add --channel telegram --token 'YOUR_TOKEN'"
echo "4. Set up your domain / SSL if needed"
