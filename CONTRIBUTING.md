# Contributing to TinyNetUse

Thanks for helping improve TinyNetUse. Keep changes focused on its purpose as a small Windows network-speed utility.

## Before starting

- Use the issue forms for bugs and feature requests.
- Check existing issues before opening a new one.
- For a larger behavior change, open an issue before writing the code.
- Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Development setup

Clone the repository, then follow [DEVELOPMENT.md](DEVELOPMENT.md) for the Python environment, source run, tests, and Windows build commands.

## Pull requests

1. Create a focused branch from `main`.
2. Keep unrelated cleanup out of the change.
3. Add or update useful tests when behavior changes.
4. Run `pytest` and confirm it passes.
5. Explain what changed, why, and any manual Windows testing performed.

Prefer readable Python and small direct functions. Avoid adding frameworks, services, or general system-monitor features that TinyNetUse does not need.
