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

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   python manage.py migrate
   ```

5. Add modules:
   ```bash
   git submodule add https://github.com/SolsticeOps/SolsticeOps-docker.git modules/docker
   git submodule add https://github.com/SolsticeOps/SolsticeOps-k8s.git modules/k8s
   git submodule add https://github.com/SolsticeOps/SolsticeOps-jenkins.git modules/jenkins
   ```

6. Run the server:
   ```bash
   python manage.py runserver
   ```
