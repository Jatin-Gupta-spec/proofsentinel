# PROJECT_STATE

## Current stage
Stage 3 complete. Next: Stage 4.

## Stage history
- Stage 0 accepted: spec v1.2 frozen and TriageAI tag verified (project commit e925e45)
- Stage 1 accepted: repository, dev tooling, documentation skeleton, MIT license and CI. All four CI jobs were green at commit 9669901
- Stage 2 accepted: testable CLI skeleton at commit 71854d7. All four CI jobs were green on that commit
- Stage 3 accepted: immutable data models at commit 4223dc7. All four CI jobs were green on that commit

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
- Virtual environment: .venv in the repo root. A terminal can activate it with a process-scope policy only (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned); never use a wider scope. Project commands use the explicit .\.venv\Scripts\python.exe path, so activation is optional
- Dev tools (pytest, Ruff, mypy strict, pip-audit) installed in .venv with pip install -e ".[dev]". Runtime dependencies: none

## CI
- Workflow: .github/workflows/ci.yml
- Matrix: ubuntu-latest and windows-latest, Python 3.11 and 3.13 (as the spec requires)
- Steps: upgrade pip and setuptools, install ".[dev]", pytest, Ruff, strict mypy, pip-audit
- Permissions: contents: read. Checkout uses persist-credentials: false
- Actions pinned by major version tag: actions/checkout@v6, actions/setup-python@v6

## CLI (Stage 2)
- Entry points: python -m proofsentinel (src/proofsentinel/__main__.py) and cli.main(argv) -> int in src/proofsentinel/cli.py
- Commands that parse: validate <manifest>, run <manifest> --output <dir>, verify-evidence <dir>. Parsing opens no files
- All three commands are not implemented yet and return exit code 2 (fail closed), never 0
- Exit codes are in the ExitCode IntEnum: OK 0, CHECKS_FAILED 1, ERROR 2, USAGE 3. Usage errors return 3 with no traceback (argparse's default of 2 is overridden). --help returns 0
- Text echoed back from the command line has non-printable characters (escape characters, newlines) shown as visible escapes
- Tests set NO_COLOR and PYTHON_COLORS=0 so argparse output stays plain on newer Pythons
- Test lesson: changing the unimplemented-command return code to 0 passed Ruff and mypy but failed 3 behavior tests

## Data models (Stage 3)
- Module: src/proofsentinel/models.py. Tests: tests/test_models.py. 47 tests pass in total
- 14 dataclasses (Limits, TargetDescriptor, CanaryRegistration, Assertion, CheckDefinition, Manifest, InvocationResult, AssertionResult, CheckResult, Totals, CanonicalResults, RunMetadata, EvidenceIndexEntry, EvidenceIndex), all frozen, slotted and keyword-only. A generic test enforces this for every model class
- StrEnums: CheckType (the 7 v0.1 check types), CheckStatus (PASS, FAIL, ERROR only; no SKIP), AssertionKind, GitObjectFormat, CompletionState
- Hard ceilings from the contract are constants (200 checks, 100 invocations, 600 s per command, 1800 s overall, 1 MiB streams, argv limits, 100 MiB file hashing). Stage 4 enforces them
- Defaults fail closed: expected_exit 0, require_clean_git True
- CanaryRegistration.value is hidden from repr(), but dataclasses.asdict() still exposes it (shown in the Stage 3 exercise). Rule for Stage 9: the evidence writer must never receive a Manifest or CanaryRegistration. It accepts only result models and converts them with explicit, hand-written field lists, never asdict() or vars(). The whole-bundle canary scan (Stage 12) is a second layer, not the only one
- Models validate nothing. Stage 4's validator is the only door manifest data may pass through
- Test lesson: a first draft of the keyword-only test still passed with the protection removed. Breaking the code on purpose exposed it, and the test was rewritten

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
- CheckDefinition has only the fields shared by all checks. Fields specific to the file, git, release_claim, canary and performance checks are added in the stages that implement them.
- models.py has one suppression: "# noqa: S105" on CheckStatus.PASS. Ruff mistakes the status name for a password. It is a documented false positive, suppressed on that line only.
- CI runs 47 tests. Green CI shows the CLI contract and the data definitions hold, not that ProofSentinel can validate, run or verify anything yet.

## Decisions
- v0.1 scope is frozen. Any change needs an entry here first.
- License: MIT. The copyright notice uses the GitHub handle Jatin-Gupta-spec (can be changed before wider publication).
- requires-python >= 3.11. Runtime uses the standard library only.
- Time-box / stop rule: not set yet (owner to decide).

## Next
Stage 4: safe bounded strict-UTF-8 TOML reading and closed-schema validation. It enforces the hard ceilings in models.py and builds a Manifest only from validated data. Nothing is executed.