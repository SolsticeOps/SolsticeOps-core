# SolsticeOps-core

SolsticeOps is a modular DevOps management dashboard.

## Architecture
This is the core component which provides:
- User authentication
- Module registration and loading
- Server statistics and dashboard
- Generic tool management
- Terminal session management

## Documentation
Detailed documentation is available in the `docs/` directory.
- [Installation](docs/installation.md)
- [Creating Modules](docs/module_creation.md)
- [API Reference](docs/api_reference.md)

## Modules
SolsticeOps uses Git submodules for its modules. Available modules:
- [Docker](https://github.com/SolsticeOps/SolsticeOps-docker)
- [Kubernetes](https://github.com/SolsticeOps/SolsticeOps-k8s)
- [Jenkins](https://github.com/SolsticeOps/SolsticeOps-jenkins)
