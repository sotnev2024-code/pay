#!/bin/bash
# Deploy Telegram Pay Bot on Linux VPS (no Caddy — используйте свой nginx/прокси).
# Usage:
#   curl -sSL https://raw.githubusercontent.com/sotnev2024-code/pay/main/scripts/deploy-vps.sh | bash -s -- https://github.com/sotnev2024-code/pay.git /opt/pay
#   # or: cd /opt/pay && ./scripts/deploy-vps.sh

set -e
GITHUB_REPO="${1:-}"
INSTALL_DIR="${2:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[*] Telegram Pay Bot — VPS deploy (no Caddy)"
echo "[*] Install dir: $INSTALL_DIR"

# --- Clone ---
if [ -n "$GITHUB_REPO" ]; then
  if [ ! -d "$INSTALL_DIR" ] || [ -z "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]; then
    echo "[*] Cloning $GITHUB_REPO ..."
    PARENT="$(dirname "$INSTALL_DIR")"
    [ -d "$PARENT" ] || { sudo mkdir -p "$PARENT"; sudo chown "$(whoami):$(whoami)" "$PARENT"; }
    git clone "$GITHUB_REPO" "$INSTALL_DIR"
  fi
  PROJECT_ROOT="$INSTALL_DIR"
fi
cd "$PROJECT_ROOT"

if [ ! -f "$PROJECT_ROOT/requirements.txt" ] || [ ! -f "$PROJECT_ROOT/main.py" ]; then
  echo "[!] Not a project root. Run from repo root or pass repo URL."
  exit 1
fi

# --- System packages ---
if command -v apt-get &>/dev/null; then
  echo "[*] Installing system packages..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3 python3-venv python3-pip git
fi

# --- Venv ---
VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[*] Creating .venv..."
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt"

# --- .env ---
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
  sed -i 's/USE_POLLING=true/USE_POLLING=false/' "$ENV_FILE"
  echo "[!] Create .env and set: BOT_TOKEN, ADMIN_IDS, WEBAPP_URL, WEBHOOK_URL, CHANNEL_IDS, PORT (e.g. 8001)"
  echo "    nano $ENV_FILE"
  read -p "Edit .env now? [y/N] " -n 1 -r
  echo
  [[ $REPLY =~ ^[yY] ]] && "${EDITOR:-nano}" "$ENV_FILE"
else
  grep -q 'USE_POLLING=true' "$ENV_FILE" && sed -i 's/USE_POLLING=true/USE_POLLING=false/' "$ENV_FILE" || true
fi

PORT=$(grep -E '^PORT=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '\r')
PORT=${PORT:-8000}

# --- Systemd ---
SERVICE_NAME="pay-bot"
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Telegram Pay Bot (FastAPI + Webhook)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/python $PROJECT_ROOT/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo ""
echo "[*] Service: $SERVICE_NAME (port $PORT)"
echo "    Start:  sudo systemctl start $SERVICE_NAME"
echo "    Status: sudo systemctl status $SERVICE_NAME"
echo "    Logs:   journalctl -u $SERVICE_NAME -f"
echo ""
echo "[*] In nginx (or your proxy) add: proxy_pass http://127.0.0.1:$PORT; for your domain."
echo ""
read -p "Start $SERVICE_NAME now? [Y/n] " -n 1 -r
echo
[[ ! $REPLY =~ ^[nN] ]] && sudo systemctl start "$SERVICE_NAME" && sleep 1 && sudo systemctl status "$SERVICE_NAME" --no-pager || true
echo "Done."
