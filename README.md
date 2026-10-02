# ProofSentinel

An offline-first, deterministic security testing and evidence harness for authorized local Python projects.

> **Status: early development (v0.1 planned).** Only the package skeleton and development tooling exist today. Everything under "Planned" is a design goal, not a working feature.

## A harness, not a sandbox

ProofSentinel will run reviewed target code with your normal user permissions. It will apply timeouts and output limits, but it does not isolate or contain that code. Run it only on code you own or are explicitly authorized to test, and only with manifests you have reviewed. See [LIMITATIONS.md](LIMITATIONS.md) and [THREAT_MODEL.md](THREAT_MODEL.md).

## Planned for v0.1

- `python -m proofsentinel validate <manifest>`
- `python -m proofsentinel run <manifest> --output <new-directory>`
- `python -m proofsentinel verify-evidence <evidence-directory>`
- Strict UTF-8 TOML manifests, authorized local Python targets only
- Deterministic checks and an evidence bundle with a SHA-256 checksum index

## Not in v0.1

Remote agents, dashboards, cloud APIs, AI providers, plugins, containers, arbitrary executables, shell commands, signed evidence, security-certification claims.

## Development (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pip_audit
```