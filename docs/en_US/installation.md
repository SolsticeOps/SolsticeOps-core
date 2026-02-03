# Installation Guide

SolsticeOps-core is the central management system. Modules are added as Git submodules.

## Prerequisites
- Python 3.10+
- Docker (optional, but recommended for some modules)
- Git

## Setup

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

4. Initialize the database:
   ```bash
   python manage.py migrate
   ```

5. Add and initialize modules:
   ```bash
   # Add a new submodule
   git submodule add {module_repo_url} modules/{module_name}
   
   # Or if you just cloned the core with existing submodules:
   git submodule update --init --recursive

   # Install module-specific dependencies
   pip install -r modules/{module_name}/requirements.txt
   ```

6. Run the server:
   ```bash
   python manage.py runserver
   ```
