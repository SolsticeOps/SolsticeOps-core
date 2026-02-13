# Installation Guide

SolsticeOps-core is the central management system. Modules are added as Git submodules.

## Automatic Installation (Recommended)

The easiest way to install SolsticeOps is using the provided installation script. It handles dependencies, service creation, and initial configuration.

```bash
sudo ./install.sh
```

The script provides three options:
1. **Install**: Full installation of the core and selected modules.
2. **Update**: Updates the core and all modules via Git, updates dependencies, and runs migrations.
3. **Uninstall**: Stops the service and removes installation files.

## Manual Setup

If you prefer to set up the system manually, follow these steps:

### Prerequisites
- Python 3.10+
- Docker (optional, but recommended for some modules)
- Git

### Setup Steps

1. Clone the core repository:
   ```bash
   git clone https://github.com/SolsticeOps/SolsticeOps-core.git
   cd SolsticeOps-core
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install core dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the database:
   ```bash
   python setup_db.py
   ```
   Follow the interactive prompts to choose your database (SQLite, MySQL, or PostgreSQL).

5. Initialize the database:
   ```bash
   python manage.py migrate
   ```

6. Add and initialize modules:
   ```bash
   # Add a new submodule
   git submodule add {module_repo_url} modules/{module_name}
   
   # Or if you just cloned the core with existing submodules:
   git submodule update --init --recursive

   # Install module-specific dependencies
   pip install -r modules/{module_name}/requirements.txt
   ```

7. Run the server (as `root` user):
   ```bash
   sudo .venv/bin/python manage.py runserver 0.0.0.0:8000
   ```
