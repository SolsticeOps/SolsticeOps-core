#!/bin/bash

# SolsticeOps Installation Script
# This script must be run as root.

#    _____       _     _   _           ____            
#   / ____|     | |   | | (_)         / __ \           
#  | (___   ___ | |___| |_ _  ___ ___| |  | |_ __  ___ 
#   \___ \ / _ \| / __| __| |/ __/ _ \ |  | | '_ \/ __|
#   ____) | (_) | \__ \ |_| | (_|  __/ |__| | |_) \__ \
#  |_____/ \___/|_|___/\__|_|\___\___|\____/| .__/|___/
#                                           | |        
#                                           |_|        


set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVICE_FILE="/etc/systemd/system/solstice-ops.service"

show_logo() {
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
}

get_install_dir() {
    if [[ -f "$SERVICE_FILE" ]]; then
        INSTALL_DIR=$(grep WorkingDirectory "$SERVICE_FILE" | cut -d'=' -f2 | xargs)
        echo "$INSTALL_DIR"
    else
        echo ""
    fi
}

do_install() {
    echo "Welcome to the SolsticeOps installation script!"
    echo "This will install the core panel and selected modules."
    echo ""

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
    echo "*You can install these and other modules through the interface"
    read -ei "" -p "Selection [1 2 3 4]: " MODULE_CHOICE
    MODULE_CHOICE=${MODULE_CHOICE:-"1 2 3 4"}

    # 3. System dependencies
    echo -e "\n${YELLOW}--- Installing System Dependencies ---${NC}"
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git curl libmagic1 dmidecode

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
    pip install whitenoise

    # 6. Initialize submodules and install their dependencies
    echo -e "\n${YELLOW}--- Initializing Modules ---${NC}"
    for choice in $MODULE_CHOICE; do
        case $choice in
            1) 
                git submodule update --init modules/docker
                if [[ -f "modules/docker/requirements.txt" ]]; then
                    pip install -r modules/docker/requirements.txt
                fi
                ;;
            2) 
                git submodule update --init modules/k8s
                if [[ -f "modules/k8s/requirements.txt" ]]; then
                    pip install -r modules/k8s/requirements.txt
                fi
                ;;
            3) 
                git submodule update --init modules/jenkins
                if [[ -f "modules/jenkins/requirements.txt" ]]; then
                    pip install -r modules/jenkins/requirements.txt
                fi
                ;;
            4) 
                git submodule update --init modules/ollama
                if [[ -f "modules/ollama/requirements.txt" ]]; then
                    pip install -r modules/ollama/requirements.txt
                fi
                ;;
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

    echo -e "\n${YELLOW}--- Collecting Static Files ---${NC}"
    python3 manage.py collectstatic --noinput

    echo -e "\n${YELLOW}--- Creating Admin User ---${NC}"
    python3 manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='$ADMIN_USER').delete(); User.objects.create_superuser('$ADMIN_USER', 'admin@example.com', '$ADMIN_PASS')"

    # 9. Systemd service
    echo -e "\n${YELLOW}--- Creating Systemd Service ---${NC}"
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=SolsticeOps Management Panel
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
}

do_update() {
    INSTALL_DIR=$(get_install_dir)
    if [[ -z "$INSTALL_DIR" ]]; then
        echo -e "${RED}Error: SolsticeOps service not found. Cannot perform update.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}--- Updating SolsticeOps in $INSTALL_DIR ---${NC}"
    cd "$INSTALL_DIR"

    echo -e "\n${YELLOW}--- Pulling changes from Git ---${NC}"
    git pull
    # Only update submodules that are already initialized
    git submodule update --recursive

    echo -e "\n${YELLOW}--- Updating Dependencies ---${NC}"
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install whitenoise
    
    # Update module dependencies only for initialized modules
    for mod_dir in modules/*; do
        if [[ -d "$mod_dir" && -f "$mod_dir/requirements.txt" && -f "$mod_dir/__init__.py" ]]; then
            echo "Updating dependencies for module: $(basename "$mod_dir")"
            pip install -r "$mod_dir/requirements.txt"
        fi
    done

    echo -e "\n${YELLOW}--- Running Migrations ---${NC}"
    python3 manage.py migrate
    python3 manage.py collectstatic --noinput

    echo -e "\n${YELLOW}--- Restarting Service ---${NC}"
    systemctl restart solstice-ops

    echo -e "\n${GREEN}SolsticeOps updated successfully!${NC}"
}

do_uninstall() {
    INSTALL_DIR=$(get_install_dir)
    if [[ -z "$INSTALL_DIR" ]]; then
        echo -e "${RED}Error: SolsticeOps service not found. Cannot perform uninstall.${NC}"
        exit 1
    fi

    echo -e "${RED}WARNING: This will stop the service and delete the installation directory: $INSTALL_DIR${NC}"
    read -p "Are you sure you want to proceed? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Uninstall cancelled."
        exit 0
    fi

    echo -e "\n${YELLOW}--- Stopping and Disabling Service ---${NC}"
    systemctl stop solstice-ops || true
    systemctl disable solstice-ops || true
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload

    echo -e "\n${YELLOW}--- Removing Installation Directory ---${NC}"
    rm -rf "$INSTALL_DIR"

    echo -e "\n${GREEN}SolsticeOps uninstalled successfully.${NC}"
}

# Main script execution
show_logo

# 1. Root check
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root.${NC}"
   exit 1
fi

echo "Please choose an option:"
echo "1) Install"
echo "2) Update"
echo "3) Uninstall"
read -p "Option [1-3]: " MAIN_CHOICE

case $MAIN_CHOICE in
    1)
        do_install
        ;;
    2)
        do_update
        ;;
    3)
        do_uninstall
        ;;
    *)
        echo -e "${RED}Invalid option.${NC}"
        exit 1
        ;;
esac
