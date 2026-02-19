#!/usr/bin/env bash
# lume deploy script
# sets up the pi as a standalone wifi access point

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; DIM='\033[2m'; RESET='\033[0m'
log()  { echo -e "${DIM}[lume]${RESET} $1"; }
ok()   { echo -e "${GREEN}[ok]${RESET} $1"; }
warn() { echo -e "${YELLOW}[warn]${RESET} $1"; }
die()  { echo -e "${RED}[error]${RESET} $1"; exit 1; }

[[ $EUID -ne 0 ]] && die "run as root: sudo bash deploy.sh"
[[ ! -f server.py ]] && die "server.py not found — run from the lume directory"
[[ ! -f index.html ]] && die "index.html not found — run from the lume directory"

LUME_DIR=$(pwd)
WIFI_IF=$(iw dev | awk '$1=="Interface"{print $2}' | head -1)
[[ -z "$WIFI_IF" ]] && die "no wifi interface found"

PI_IP="10.42.0.1"
DHCP_RANGE_START="10.42.0.10"
DHCP_RANGE_END="10.42.0.100"
LUME_PORT="8000"

log "deploying from $LUME_DIR"
log "wifi interface: $WIFI_IF"

# ── hotspot config ─────────────────────────────────────────────────────────
echo ""
echo "access point config"
echo "─────────────────────────────"
read -rp "network name (ssid) [lume]: " AP_SSID
AP_SSID="${AP_SSID:-lume}"
echo ""

# ── install packages ───────────────────────────────────────────────────────
log "installing packages..."
apt-get update -q > /dev/null 2>&1
apt-get install -y -q \
    hostapd \
    dnsmasq \
    python3 \
    python3-pip \
    python3-venv \
    bluetooth \
    bluez > /dev/null 2>&1
ok "packages installed"

# stop services before configuring
systemctl stop hostapd dnsmasq 2>/dev/null || true
systemctl unmask hostapd 2>/dev/null || true

# ── static ip ─────────────────────────────────────────────────────────────
log "setting static ip $PI_IP on $WIFI_IF..."
sed -i "/^interface ${WIFI_IF}/,/^$/d" /etc/dhcpcd.conf 2>/dev/null || true
cat >> /etc/dhcpcd.conf << EOF

interface ${WIFI_IF}
    static ip_address=${PI_IP}/24
    nohook wpa_supplicant
EOF

# ── hostapd ────────────────────────────────────────────────────────────────
log "configuring access point..."
cat > /etc/hostapd/hostapd.conf << EOF
interface=${WIFI_IF}
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
else
    cat > /etc/hostapd/hostapd.conf << EOF
interface=${WIFI_IF}
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF
fi
chmod 600 /etc/hostapd/hostapd.conf
sed -i 's|#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

# ── dnsmasq ────────────────────────────────────────────────────────────────
log "configuring dhcp..."
[[ -f /etc/dnsmasq.conf ]] && mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
cat > /etc/dnsmasq.conf << EOF
interface=${WIFI_IF}
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},255.255.255.0,24h
domain=local
address=/lume.local/${PI_IP}
EOF

# ── python env ─────────────────────────────────────────────────────────────
log "setting up python environment..."
python3 -m venv "$LUME_DIR/.venv"
"$LUME_DIR/.venv/bin/pip" install -q websockets bleak aiohttp > /dev/null 2>&1
ok "python dependencies installed"

# ── bluetooth ──────────────────────────────────────────────────────────────
log "enabling bluetooth..."
systemctl enable --now bluetooth > /dev/null 2>&1
usermod -a -G bluetooth pi 2>/dev/null || true

# ── systemd service ────────────────────────────────────────────────────────
log "creating systemd service..."
cat > /etc/systemd/system/lume.service << EOF
[Unit]
Description=lume light controller
After=bluetooth.target hostapd.service
Wants=bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=${LUME_DIR}
ExecStart=${LUME_DIR}/.venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── start everything ───────────────────────────────────────────────────────
log "enabling and starting services..."
systemctl daemon-reload
systemctl enable hostapd dnsmasq lume > /dev/null 2>&1
systemctl restart dhcpcd 2>/dev/null || true
systemctl start hostapd
systemctl start dnsmasq
systemctl start lume
sleep 3

# ── verify ─────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────"
echo ""
systemctl is-active --quiet hostapd && ok "hostapd running" || warn "hostapd failed    — journalctl -u hostapd -n 20"
systemctl is-active --quiet dnsmasq && ok "dnsmasq running" || warn "dnsmasq failed    — journalctl -u dnsmasq -n 20"
systemctl is-active --quiet lume    && ok "lume running"    || warn "lume failed       — journalctl -u lume -n 20"

APP_URL="http://${PI_IP}:${LUME_PORT}"
echo ""
ok "deploy complete"
echo ""
log "network:  ${AP_SSID}$([ -z "$AP_PASS" ] && echo ' (open)' || echo ' (password protected)')"
log "url:      ${APP_URL}"
log "also:     http://lume.local:${LUME_PORT}"
echo ""

echo "── for your printed qr codes ────────────────────────────"
echo ""
echo "  qr code 1 — join wifi"
if [[ -n "$AP_PASS" ]]; then
    echo "  encode: WIFI:T:WPA;S:${AP_SSID};P:${AP_PASS};;"
else
    echo "  encode: WIFI:T:nopass;S:${AP_SSID};;"
fi
echo ""
echo "  qr code 2 — open app"
echo "  encode: ${APP_URL}"
echo ""
echo "  use any qr generator (e.g. qr-code-generator.com)"
echo "  print both and stick them on the wall."
echo ""
echo "────────────────────────────────────────────────────────"
echo ""
log "useful commands:"
log "  logs:     journalctl -u lume -f"
log "  restart:  systemctl restart lume"
log "  status:   systemctl status lume hostapd dnsmasq"
echo ""

