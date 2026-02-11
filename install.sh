#!/bin/bash

# SolsticeOps Installation Script
# This script must be run as root.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"

echo "   _____       _     _   _           ____                 "
echo "  / ____|     | |   | | (_)         / __ \\               "
echo " | (___   ___ | |___| |_ _  ___ ___| |  | |_ __  ___      "
echo "  \\___ \\ / _ \\| / __| __| |/ __/ _ \\ |  | | '_ \\/ __|"
echo "  ____) | (_) | \\__ \\ |_| | (_|  __/ |__| | |_) \\__ \\ "
echo " |_____/ \\___/|_|___/\\__|_|\\___\\___|\\____/| .__/|___/"
echo "                                          | |             "
echo "                                          |_|             "

echo -e "${NC}"
echo "Welcome to the SolsticeOps installation script!"
echo "This will install the core panel and selected modules."
echo ""

# 1. Root check
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root.${NC}"
   exit 1
fi

# 2. Interactive configuration
echo -e "${YELLOW}--- Configuration ---${NC}"

read -ei "/opt/solstice-ops" -p "Installation directory: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-/opt/solstice-ops}

read -ei "8000" -p "Web panel port: " PANEL_PORT
PANEL_PORT=${PANEL_PORT:-8000}

read -ei "admin" -p "Admin username: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

read -s -p "Admin password: " ADMIN_PASS
echo ""
if [[ -z "$ADMIN_PASS" ]]; then
    echo -e "${RED}Error: Admin password cannot be empty.${NC}"
    exit 1
fi

echo ""
echo "Select modules to install (space separated numbers):"
echo "1) Docker (Container management)"
echo "2) Kubernetes (Cluster management)"
echo "3) Jenkins (CI/CD automation)"
echo "4) Ollama (AI Models)"
read -ei "1 2 3 4" -p "Selection: " MODULE_CHOICE
MODULE_CHOICE=${MODULE_CHOICE:-"1 2 3 4"}

# 3. System dependencies
echo -e "\n${YELLOW}--- Installing System Dependencies ---${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv git curl libmagic1

# 4. Clone repository
echo -e "\n${YELLOW}--- Cloning Repository ---${NC}"
if [[ -d "$INSTALL_DIR" ]]; then
    echo -e "${YELLOW}Warning: Directory $INSTALL_DIR already exists. Backing up to ${INSTALL_DIR}.bak${NC}"
    mv "$INSTALL_DIR" "${INSTALL_DIR}.bak"
fi

git clone https://github.com/SolsticeOps/SolsticeOps-core.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 5. Virtual environment
echo -e "\n${YELLOW}--- Setting up Virtual Environment ---${NC}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Initialize submodules
echo -e "\n${YELLOW}--- Initializing Modules ---${NC}"
for choice in $MODULE_CHOICE; do
    case $choice in
        1) git submodule update --init modules/docker ;;
        2) git submodule update --init modules/k8s ;;
        3) git submodule update --init modules/jenkins ;;
        4) git submodule update --init modules/ollama ;;
    esac
done

# 7. Create .env file
echo -e "\n${YELLOW}--- Creating Configuration ---${NC}"
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
cat > .env <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=*
DATABASE_URL=sqlite:///db.sqlite3
CSRF_TRUSTED_ORIGINS=http://localhost:$PANEL_PORT,http://127.0.0.1:$PANEL_PORT
PORT=$PANEL_PORT
EOF

# 8. Database and Admin user
echo -e "\n${YELLOW}--- Initializing Database ---${NC}"
python3 manage.py migrate

echo -e "\n${YELLOW}--- Creating Admin User ---${NC}"
python3 manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='$ADMIN_USER').delete(); User.objects.create_superuser('$ADMIN_USER', 'admin@example.com', '$ADMIN_PASS')"

# 9. Systemd service
echo -e "\n${YELLOW}--- Creating Systemd Service ---${NC}"
cat > /etc/systemd/system/solstice-ops.service <<EOF
[Unit]
Description=SolsticeOps Management Panel
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin"
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/manage.py runserver 0.0.0.0:$PANEL_PORT
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable solstice-ops
systemctl start solstice-ops

# 10. Final output
echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}SolsticeOps installed successfully!${NC}"
echo -e "Access the panel at: ${YELLOW}http://$(curl -s ifconfig.me):$PANEL_PORT${NC}"
echo -e "Admin username: ${YELLOW}$ADMIN_USER${NC}"
echo -e "Service status: ${YELLOW}systemctl status solstice-ops${NC}"
echo -e "${GREEN}====================================================${NC}"
