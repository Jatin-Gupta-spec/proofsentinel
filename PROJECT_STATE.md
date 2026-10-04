# PROJECT_STATE

## Current stage
Stage 1 complete. Next: Stage 2.

## Stage history
- Stage 0 accepted: spec v1.2 frozen and TriageAI tag verified (project commit e925e45)
- Stage 1 accepted: repository, dev tooling, documentation skeleton, MIT license and CI. All four CI jobs were green at commit 9669901

## Repository
- https://github.com/Jatin-Gupta-spec/proofsentinel (branch main)
- Commits use the GitHub noreply address
- Open item: confirm the GitHub setting "Block command line pushes that expose my email" is enabled

## Environment (from real command output)
- Python 3.14.6 (only install, py launcher default): %LOCALAPPDATA%\Programs\Python\Python314\python.exe
- Git 2.55.0.windows.2
- VS Code 1.140.0 (x64)
- Windows PowerShell 5.1.26100.9549
- Project root contains a space: D:\cyber projects\ (quote paths in PowerShell)
- Virtual environment: .venv in the repo root. VS Code activates it in the integrated terminal; commands still use the explicit .\.venv\Scripts\python.exe path
- Dev tools (pytest, Ruff, mypy strict, pip-audit) installed in .venv with pip install -e ".[dev]". Runtime dependencies: none

## CI
- Workflow: .github/workflows/ci.yml
- Matrix: ubuntu-latest and windows-latest, Python 3.11 and 3.13 (as the spec requires)
- Steps: upgrade pip and setuptools, install ".[dev]", pytest, Ruff, strict mypy, pip-audit
- Permissions: contents: read. Checkout uses persist-credentials: false
- Actions pinned by major version tag: actions/checkout@v6, actions/setup-python@v6

## Frozen inputs
- Spec: spec\ProofSentinel_Final_Project_Specification_Audited_v1.2.md
- Spec size: 41283 bytes
- Spec SHA-256: D7EEF7067C2B89ADE460AEA3CB5592A03C0DE063F9CEE485BF95D643DE3F7CF3
- TriageAI tag: v0.1.0 (annotated)
- TriageAI commit: 7c1aa86e6253dda3ff23c510bce0cf74da01c036
- TriageAI working tree clean when checked
- TriageAI tests at that commit: 424 passed, 7 skipped

## Known limitations (recorded, not hidden)
- 7 TriageAI tests skipped: tests\test_input_links.py:31, "cannot create symlinks in this environment". Symlink handling is not exercised on this machine.
- The same limitation will affect ProofSentinel's link and reparse tests (Stage 5). Decide how to handle it then.
- Windows PowerShell 5.1 writes UTF-16 with ">" redirection. Write manifests in the VS Code editor as UTF-8, not with ">".
- pip-audit cannot audit proofsentinel itself (not on PyPI). It audits the CI environment after pip and setuptools are upgraded.
- CI runner Python 3.11 ships setuptools 79.0.1, flagged by PYSEC-2026-3447. CI upgrades to setuptools>=83.0.0 before auditing. The finding was fixed, not suppressed.
- Local Python (3.14) is newer than the CI versions (3.11 and 3.13). 3.14 is not in the CI matrix.
- GitHub Actions are pinned by major version tag, not commit ID. Pinning by commit ID is a deferred hardening step. actions/setup-python v7 appears to exist and has not been reviewed.
- Working-tree files use CRLF line endings (VS Code on Windows). Decide a line-ending policy before Stage 13 hashes repository files.
- CI currently runs a single smoke test. Green CI shows the tooling works, not that ProofSentinel works.

## Decisions
- v0.1 scope is frozen. Any change needs an entry here first.
- License: MIT. The copyright notice uses the GitHub handle Jatin-Gupta-spec (can be changed before wider publication).
- requires-python >= 3.11. Runtime uses the standard library only.
- Time-box / stop rule: not set yet (owner to decide).

## Next
Stage 2: create the package entry point and a testable cli.main(argv) -> int. Usage errors return code 3 without a traceback; --help returns 0.