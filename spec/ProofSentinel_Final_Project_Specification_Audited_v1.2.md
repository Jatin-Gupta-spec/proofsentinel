# ProofSentinel

## Deterministic Security Testing and Evidence Harness

**Final Project Specification and Mentorship Plan — v0.1, audited revision 1.2**

> **Decision:** BUILD IN STAGES. Target tools make claims; deterministic checks test those claims; evidence records the result; a human approves the release.

Prepared for Windows 11, Visual Studio Code, beginner-to-intermediate Python learners, TriageAI and SecureGuard, GitHub Actions, and a cybersecurity portfolio.

---

## 1. Project statement

ProofSentinel is an offline-first, evidence-oriented assurance harness for authorized local cybersecurity projects. It reads a strict, human-reviewed declarative manifest, validates the requested checks, runs explicitly approved Python module commands without a shell, applies deterministic assertions, checks repeatability and synthetic-secret leakage, and produces bounded JSON and Markdown evidence. The manifest is trusted configuration: schema validation prevents malformed or accidentally unsafe plans, but does not make an adversarial manifest safe.

ProofSentinel does **not** decide whether software is secure in every environment. It does not execute arbitrary shell strings, scan remote systems, exploit targets, run malware, provide a security sandbox, or allow AI to determine pass/fail. A passing run proves only that the declared checks passed under the recorded environment and limits.

**Central principle:**

> Security claims are hypotheses. Deterministic tests produce evidence. A human owns the release decision.

## 2. Problem and target user

### Problem

Security portfolio projects often claim that tests passed, secrets were protected, outputs were deterministic, limits were enforced, or a release was reproducible. These claims are frequently recorded manually and can become stale, incomplete, or misleading.

### Target user

- Cybersecurity students and portfolio builders
- SOC and security-engineering interns
- Developers of local defensive-security tools
- Reviewers who need reproducible release evidence

### Contribution

ProofSentinel provides a small, transparent and auditable framework that turns declared security claims into repeatable checks. TriageAI is the first target; SecureGuard becomes the second target after the generic core works.

## 3. What ProofSentinel proves—and what it does not

A successful run can prove that, for the recorded revision and environment:

- Approved commands returned expected exit codes.
- Required and forbidden bounded-output assertions held.
- Repeated commands produced byte-identical output when required, after only explicitly declared transformations.
- Declared input limits failed closed with no partial report.
- Synthetic canary values did not appear unredacted in persisted evidence.
- Expected files, hashes, and Git state conditions were present.
- Runtime and output remained within declared budgets.
- A reproducible evidence bundle and checksum index were generated.

A successful run does **not** prove:

- Absence of every vulnerability or secret.
- Safety of untested inputs, platforms, configurations, or dependencies.
- Correctness of production infrastructure.
- Isolation from the host operating system.
- That a checksum index is cryptographically signed or tamper-proof.
- That AI output is factual.

## 4. Locked v0.1 scope

| Area | v0.1 requirement |
|---|---|
| Targets | Authorized local Python projects only; TriageAI is the first target. |
| Manifest | One strict UTF-8 `proofsentinel.toml`; no includes, templates, remote manifests, or plugins. |
| Commands | Python executable plus module and argument array; `shell=False`; no shell command strings. |
| Checks | Exit code, exact substring presence/absence, output-size and duration budgets, deterministic reruns, file existence/hash, Git cleanliness/tag consistency, and synthetic-canary leakage. |
| Output | Canonically serialized `results.json`, variable `run-metadata.json`, human-readable `report.md`, sanitized bounded stream artifacts, and `checksums.sha256`. Only checks explicitly declared as `determinism` make repeated-output equality claims. |
| AI | No AI provider in v0.1. AI may tutor during development but has no runtime role. |
| Runtime | Python 3.11+ standard library where practical. pytest, Ruff, mypy and pip-audit are development-only. |
| Safety | Trusted source projects and synthetic fixtures only; no malware, production logs, remote targets, or arbitrary shell execution. |

### Locked CLI

```text
python -m proofsentinel validate <manifest>
python -m proofsentinel run <manifest> --output <new-directory>
python -m proofsentinel verify-evidence <evidence-directory>
```

Optional v0.1 flags:

```text
--python <path>                 Approved target Python interpreter
--format text|markdown|json     Console summary only
```

`validate` parses, resolves and displays the bounded execution plan but launches no Python module or Git subprocess. `verify-evidence` reads evidence only and never executes target code. `run` must refuse an existing output directory; v0.1 has no `--overwrite` option.

## 5. Trust and execution model

ProofSentinel is a **test harness, not a sandbox**. Running `python -m pytest` or another target module executes trusted target-project code with the current user's operating-system permissions. The manifest is also trusted and must be reviewed and version-controlled. Its module list records human approval; it is not an independent authorization boundary.

Therefore v0.1 requires all of the following:

1. The target project is locally owned or explicitly authorized.
2. Its source and manifest have been reviewed before execution. Never run a manifest supplied by an untrusted project or person.
3. The Python executable is supplied explicitly or resolved from a validated target virtual environment.
4. Every command is represented as a Python module plus an argument list.
5. `subprocess` uses `shell=False` and never concatenates a command string.
6. The working directory is a canonical target root.
7. Time and captured-output limits apply to every process.
8. A timed-out or over-limit process is terminated; the check fails closed.
9. ProofSentinel never claims that these controls provide OS isolation.

### Permanent safety rules

- Never run unreviewed manifests or manifests downloaded from strangers; validation is not a sandbox.
- Never execute arbitrary shell strings, PowerShell snippets, batch files, or event/log content.
- Never run malware, exploit code, encoded payloads, or unknown attachments.
- The ProofSentinel core opens no network connections in v0.1, and manifests must not request networked operations. ProofSentinel provides no OS-level network isolation and cannot prevent reviewed target code from opening a connection.
- Never collect real credentials, tokens, cookies, private keys, or production logs.
- Never permit AI to create, alter, waive, or override a pass/fail result.
- Never silently convert an infrastructure error into a test pass.

## 6. Operational contract

| Item | Locked default |
|---|---|
| Manifest encoding | Strict UTF-8 without BOM; reject UTF-8/16/32 BOMs, duplicate TOML keys, invalid types and unknown keys. |
| Manifest size | Stat before read; binary bounded read of at most 1 MiB + 1 byte; reject if the extra byte exists. |
| Check count | Maximum 200 checks and 100 command invocations after expanding all repetitions. Calculate and validate the complete plan before execution; harness-owned metadata observations use separate fixed limits. |
| Paths | Canonical absolute comparison; target inputs must remain under the target root. Reject symlink/junction target roots and evidence paths inside the target tree. |
| Python executable | The selected interpreter entry path must be under the canonical target root. A standard virtual-environment symlink is allowed on platforms that create one, but its complete chain must resolve to an existing regular file; other link/reparse ambiguity is rejected. Record only a portable alias and bounded `--version` output, never the raw absolute path in portable evidence. Target commands run only through the resolved interpreter. |
| Command form | `python -m <approved_module> <argv...>`; argv is a list with at most 128 items, 4,096 UTF-8 bytes per item and 16 KiB total, with NUL forbidden. No shell, pipes, redirection, substitutions, glob expansion, or environment-variable interpolation. Metacharacters remain inert argument text. |
| Approved modules | Exact human-reviewed list declared in the trusted manifest and validated against `^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$`. This list records approval but cannot make an adversarial manifest safe. Initial examples: target CLI module, `pytest`, `ruff`, and `mypy`; network-dependent modules such as `pip_audit` are not runtime target checks in v0.1. |
| Timeout | Default 60 seconds per command; manifest may lower it or raise it to a hard maximum of 600 seconds. Overall run maximum: 1,800 seconds. |
| Output | Concurrently capture stdout and stderr as bounded raw bytes, maximum 1 MiB each per invocation. Exceeding a limit terminates the direct process, attempts best-effort process-group cleanup, marks the check `ERROR`, and stops scheduling further target commands. |
| Environment | Manifest cannot set environment variables. Inherit only `PATH`, `SYSTEMROOT`, `WINDIR`, `COMSPEC`, `PATHEXT`, `TEMP`, `TMP`, `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `LANG` and `LC_ALL` when present; force `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `PYTHONHASHSEED=0`, and `NO_COLOR=1`. Record inherited variable names and presence only, not their raw values or hashes. |
| Hashes and determinism | For each stream record `raw_sha256` over the bounded raw bytes before decoding/redaction and `persisted_sha256` over the exact sanitized bytes written to evidence. Assertions and determinism use `raw_sha256`; `checksums.sha256` and `verify-evidence` use persisted artifact bytes. No timestamp, path or newline normalization is implicit. |
| Evidence directory | Fully preflight before creation; must not already exist and must be outside the target repository. Create atomically with restrictive permissions where supported and immediately add `INCOMPLETE`; remove that marker only after every final artifact and checksum has been safely committed. |
| Canary handling | Raw values may appear only in the trusted manifest `[canaries]` registry and controlled synthetic fixtures, never argv, IDs or filenames. Every value must be unique ASCII matching `^PS_TEST_[A-Z0-9_]{8,120}$` (minimum total length 16). Scan streams, command labels, results, reports, exceptions, console text and logs before persistence; replace matches with a fixed token and record only label, count and a domain-separated safe hash. Scan the completed bundle again before acceptance. |
| Assertions | Search for the UTF-8 encoding of declared strings in bounded raw bytes. Persist text decoded with UTF-8 replacement and record whether replacements occurred. Canary sanitization precedes persistence; context escaping follows it. |
| File hashing | Regular files only, no links/devices/pipes; stream SHA-256 up to a hard 100 MiB maximum and verify file identity before and after reading. |
| Git executable | Harness-owned Git observations use one resolved trusted `git` binary, bounded output/time, and fixed internal argv templates. Release tags must match `^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$`, must not contain `..`, and can never become Git options. |
| JSON | UTF-8, sorted keys, compact canonical form, final newline, non-finite numbers rejected. Check results and variable run metadata are separate files; canonical serialization does not imply two executions produce identical observations. |
| Markdown | Fixed section order and escaping of attacker-controlled text. |
| Git object IDs | Accept a full 40- or 64-character hexadecimal object ID according to the repository object format; abbreviations are rejected. |
| Interruptions | On `Ctrl+C`, stop scheduling checks, terminate the active direct process, attempt best-effort group cleanup, sanitize and flush safe partial artifacts, retain `INCOMPLETE`, and exit 2. |
| Exit codes | `0` all declared checks passed; `1` one or more checks failed; `2` manifest, safety, execution or evidence-integrity error; `3` command-line usage error. Override `argparse.ArgumentParser.error()` so parser mistakes return 3 without a traceback; `--help` remains 0. |
| Partial evidence | A preflight error creates no output directory. After execution begins, write through temporary files and atomic replacement. On interruption or infrastructure failure retain sanitized partial evidence with `INCOMPLETE`; `verify-evidence` must reject it. |

## 7. Manifest model

The TOML schema is closed: unknown sections and keys are errors.

```toml
schema_version = 1

[target]
name = "TriageAI"
root = "../triageai"
python = ".venv/Scripts/python.exe"
expected_git_commit = "<full 40- or 64-character Git object ID>"
require_clean_git = true

[limits]
command_timeout_seconds = 60
overall_timeout_seconds = 1800
stdout_bytes = 1048576
stderr_bytes = 1048576

[modules]
allow = ["triageai", "pytest", "ruff", "mypy"]

[canaries]
fake_api_token = "PS_TEST_API_TOKEN_7K4M2Q9X"

[[checks]]
id = "quality-pytest"
type = "command"
module = "pytest"
args = ["-q"]
expected_exit = 0
stdout_contains = ["passed"]

[[checks]]
id = "deterministic-auth-case"
type = "determinism"
module = "triageai"
args = ["analyze", "tests/fixtures/suspicious/SC-AUTH001-bruteforce.json"]
repetitions = 2
expected_exit = 0

[[checks]]
id = "record-cap-fails-closed"
type = "command"
module = "triageai"
args = ["analyze", "proofsentinel-fixtures/10001-records.json"]
expected_exit = 2
stdout_exact = ""
stderr_contains = ["10,000-record cap"]

[[checks]]
id = "release-tag-claim"
type = "release_claim"
source_file = "ACCEPTANCE.md"
required_text = "Release tag: `v0.1.0`"
tag = "v0.1.0"
must_point_to_expected_commit = true
```

This is illustrative, not implementation code. The final schema must be documented and tested before the runner is built.

## 8. Core data models

```text
Manifest
├── schema_version
├── target
├── limits
├── approved_modules
└── checks

TargetDescriptor
├── name
├── root
├── python_executable
├── expected_git_commit
└── require_clean_git

CheckDefinition
├── id
├── type
├── module / argv
├── expected_exit
├── assertions
├── timeout
├── repetitions
└── canary_labels referencing the manifest registry

InvocationResult
├── sanitized_command_label
├── exit_code
├── duration_ms
├── stdout_size / stderr_size
├── stdout_raw_sha256 / stderr_raw_sha256
├── stdout_persisted_sha256 / stderr_persisted_sha256
├── timed_out / output_limited
└── sanitized_artifact_paths

CheckResult
├── check_id
├── status: PASS | FAIL | ERROR
├── assertions
├── invocations
└── safe_reason

CanonicalResults
├── schema_version / proofsentinel_version
├── raw_manifest_sha256
├── target_revision and Git object format
├── check results, output hashes and statuses without timings or local absolute paths
├── totals
├── overall_status
└── not_run_check_ids

RunMetadata
├── schema_version / proofsentinel_version
├── environment aliases and safe hashes
├── invocation durations and resource observations
├── decoding-replacement flags
└── completion state
```

### Required distinction

| Category | Meaning |
|---|---|
| Observation | Directly measured value: exit code, duration, byte count, hash, file state. |
| Assertion result | Deterministic comparison between an observation and a declared expectation. |
| Harness error | ProofSentinel could not safely or completely perform the check. |
| Interpretation | Human explanation of what the evidence may mean. It cannot change status. |
| Release decision | Human-owned decision outside ProofSentinel. |

Status rules are closed: `PASS` means the check completed and all assertions passed; `FAIL` means it completed and at least one declared assertion failed; `ERROR` means it could not be completed safely or correctly. Expected nonzero target exits can pass; an exit-code mismatch fails; launch failure, timeout or output overflow errors. Ordinary `FAIL` results do not stop later checks. After `ERROR`, stop scheduling target commands, list remaining IDs under `not_run_check_ids`, finalize sanitized evidence if integrity is intact, and exit 2. Crashes, interruption or unsafe evidence failure retain `INCOMPLETE`. v0.1 has no `SKIP` state.

## 9. Check catalogue for v0.1

### `command`
Runs one approved Python module command and checks exit code plus bounded exact-substring assertions.

### `determinism`
Runs the same approved command two or more times. It compares selected bounded raw bytes through `raw_sha256` or explicitly declared artifact hashes. Persisted evidence integrity separately uses `persisted_sha256`. Transformations must be explicit; timestamps, paths and newlines are not silently normalized.

### `file`
Checks that an expected regular file exists under the target root, optionally comparing streaming SHA-256. It does not follow links, rejects non-regular or changing files, and enforces the 100 MiB cap.

### `git`
Uses only fixed harness-owned Git argv templates to check repository cleanliness, full HEAD object ID, repository object format, expected tag-to-commit relationship and optional tracked-artifact rules. It records observations and never accepts manifest-controlled Git options.

### `release_claim`
Checks for one exact declared statement in a strict UTF-8 regular documentation file bounded to 1 MiB, then mechanically verifies the referenced tag and expected commit. It does not interpret general natural language.

### `canary`
Runs an approved fixture containing explicitly synthetic values and proves that raw canaries do not appear in the selected output. If leakage occurs, persisted artifacts redact the raw canary while retaining deterministic evidence of the failure.

### `performance`
Measures wall-clock duration and output size against generous declared budgets. Results are environment-specific and must not be presented as universal benchmarks.

## 10. Evidence model

A successful or ordinary failed run produces:

```text
evidence/
├── results.json
├── run-metadata.json
├── report.md
├── checksums.sha256
└── streams/
    ├── <check-id>-01.stdout.txt
    └── <check-id>-01.stderr.txt
```

Requirements:

- `results.json` uses canonical serialization for statuses, assertions and observed output hashes; `run-metadata.json` contains durations, environment observations and other variable measurements. Neither file is claimed identical across independent runs unless a specific check says so.
- Results are sorted by manifest check order. Check IDs are unique and match `^[a-z][a-z0-9-]{0,63}$`; Windows reserved device names, trailing spaces and trailing periods are rejected.
- Stream names derive only from validated check IDs.
- Captured streams are bounded and sanitized before persistence.
- Every persisted stream records both `raw_sha256` and `persisted_sha256`. `checksums.sha256` uses the persisted file bytes only, lowercase hex, two spaces, sorted relative POSIX paths, and covers every evidence file except itself.
- `verify-evidence` detects missing, changed, unlisted extra or linked files and rejects `INCOMPLETE`. The extra-file allow-list is empty in v0.1.
- Checksums provide accidental/modification detection, not authorship or non-repudiation.
- Portable aliases apply only to fields generated by ProofSentinel itself. Captured target streams preserve target-emitted path text except required canary/control-context sanitization; `LIMITATIONS.md` must warn that target output can reveal local paths. The machine hostname and username are omitted from harness-written fields.
- The report states the exact scope and limitations of the run.
- Reports never use “secure,” “vulnerability-free,” “tamper-proof,” or “certified” as an automatic conclusion.

## 11. Threat model

| Threat | Required control | Residual risk |
|---|---|---|
| Shell injection | `shell=False`; executable/module/argv kept separate; no shell syntax | Trusted Python target code can still perform arbitrary actions with user permissions |
| Unreviewed or adversarial manifest | Policy forbids execution; manifest and target must be human-reviewed and version-controlled | Schema validation cannot make an adversarial manifest safe |
| Path traversal | Canonical containment checks; reject unsafe roots and evidence paths | Filesystem races cannot be fully removed portably |
| Symlink/junction escape | Reject known links at validation and verify identity before sensitive reads/writes | Platform-specific races and reparse-point behavior remain |
| Process hang | Per-command and overall timeouts; new process group/session; terminate direct process and attempt best-effort group/descendant cleanup | Detached or hostile descendants may survive without stronger OS isolation |
| Output flooding | Concurrent bounded binary capture; terminate on cap | Data emitted elsewhere by target code is outside capture |
| Secret leakage | Synthetic-only policy, in-memory scan, sanitize before persistence | Pattern-based scanning cannot prove absence of unknown secrets |
| Evidence tampering | SHA-256 index and verification command | Unsigned hashes can be regenerated by an attacker with write access |
| Stale release claim | Exact `release_claim` text plus mechanical Git tag/commit verification | General prose and external CI claims are not interpreted; trusted CI import is deferred |
| Prompt injection | No AI runtime in v0.1; all target output is inert text | Future AI explanation requires a separate trust boundary |
| Denial of service | Manifest, check, runtime and output limits | CPU/memory limits are advisory without OS/container isolation |

## 12. Architecture

```text
proofsentinel/
├── .github/workflows/ci.yml
├── pyproject.toml
├── README.md
├── SECURITY.md
├── PRIVACY.md
├── THREAT_MODEL.md
├── LIMITATIONS.md
├── RULES.md
├── CHANGELOG.md
├── RELEASE_CHECKLIST.md
├── LICENSE
├── src/proofsentinel/
│   ├── __main__.py
│   ├── cli.py
│   ├── constants.py
│   ├── models.py
│   ├── errors.py
│   ├── manifest.py
│   ├── paths.py
│   ├── execution.py
│   ├── capture.py
│   ├── assertions.py
│   ├── determinism.py
│   ├── canaries.py
│   ├── git_checks.py
│   ├── evidence.py
│   ├── verification.py
│   └── reporters/{terminal,markdown,json_report}.py
└── tests/
    ├── fixtures/{manifests,targets,hostile}/
    ├── test_manifest.py
    ├── test_paths.py
    ├── test_execution.py
    ├── test_capture.py
    ├── test_assertions.py
    ├── test_determinism.py
    ├── test_canaries.py
    ├── test_git_checks.py
    ├── test_evidence.py
    ├── test_verification.py
    └── test_regressions.py
```

No plugin system, YAML parser, database, web interface, remote runner, container orchestrator or AI provider exists in v0.1.

## 13. Test plan

Required automated tests include:

- Valid minimal manifest and every allowed check type.
- Unknown key, duplicate key, wrong type, invalid identifier, missing field and unsupported schema version.
- Zero-byte, BOM, non-UTF-8, oversized and truncated manifests.
- Target-root, parent traversal, absolute path, symlink and Windows-junction cases.
- Argument tokens containing spaces and shell metacharacters proving they remain inert argv values.
- A regression test that would fail if `shell=True` were introduced.
- Exit codes 0, 1, 2, usage code 3, `--help` code 0, argparse parse errors without traceback, and unusual target nonzero values.
- Timeout, direct-process termination and best-effort cooperative-child cleanup behavior on each supported OS; tests must not claim all hostile descendants are contained.
- Stdout-only, stderr-only, interleaved and simultaneous output flooding without deadlock.
- Exact boundary and one-byte-over tests for both streams.
- Unicode, invalid-output-byte, UTF-8 replacement, newline and raw-byte assertion handling.
- Required/forbidden substring assertions and empty output.
- Two identical raw runs, two different raw runs, raw-versus-persisted hash divergence after redaction, and explicit no-hidden-normalization tests.
- Canary registry tests cover required `PS_TEST_` prefix, 16-character minimum, allowed ASCII, uniqueness, maximum length, absent values, one leak, repeated leaks, chunk-split leaks and stderr leaks.
- Proof that a leaked raw canary never enters persisted evidence, command labels, console output, logs, exceptions or filenames, including matches split across capture chunks.
- A final whole-bundle canary scan that fails closed if any raw value survives.
- Simultaneous stdout/stderr flooding at exact limits and one byte over without deadlock.
- Clean/dirty Git state, detached HEAD, 40/64-character object IDs, absent tag, wrong tag target and exact `release_claim` mismatch.
- Evidence filename safety including Windows reserved names, deterministic ordering, atomic writes, interruption/`Ctrl+C`, `INCOMPLETE`, checksum generation, modification, deletion, link and extra-file detection.
- Malicious Markdown/HTML and terminal-control sequences rendered inert.
- TriageAI adapter manifest tested end to end without target-specific logic in the core.
- Serializing the same in-memory result model twice produces byte-identical JSON; independent executions are compared only by declared `determinism` checks, not by a blanket whole-report claim.

CI must run pytest, Ruff, strict mypy and pip-audit on Ubuntu and Windows using Python 3.11 and 3.13.

## 14. Acceptance gate

| Gate | Pass condition |
|---|---|
| Safety | No shell command strings; hostile argv remains inert; limits fail closed; trusted-local-target warning is prominent. |
| Correctness | All observation and assertion statuses follow the documented state machine. |
| Evidence integrity | Every persisted artifact is bounded, sanitized and covered by persisted-byte checksums; raw hashes remain distinct and are used only for assertions/determinism. |
| Privacy | Raw planted canaries appear nowhere in persisted outputs, errors or logs. |
| Determinism | Canonical serialization is stable, and every declared `determinism` check proves equality of its selected bounded bytes/hashes after only explicit transformations; whole-run evidence is not claimed byte-identical. |
| Portability | Required Windows and Ubuntu tests execute rather than being silently skipped. |
| Documentation | README, security/privacy/threat/limitations docs, schema reference, examples and release checklist exist; LIMITATIONS explicitly states that captured target streams may retain target-emitted local paths. |
| Independence | Core code contains no hard-coded TriageAI or SecureGuard rule; targets are expressed through manifests. |
| Reproducibility | Clean source archive installs and passes the full suite in a fresh environment. |

## 15. Development roadmap

| Version | Deliverable | Acceptance evidence |
|---|---|---|
| 0.1 | Local Python-target manifest validation, bounded runner, deterministic assertions, canary scanning, evidence bundle, TriageAI target manifest | Full fixture suite and clean-source verification pass on Windows and Ubuntu |
| 0.2 | SecureGuard target pack, stronger Windows process-tree control, optional resource monitoring | Target-neutral core remains unchanged; cross-platform termination tests pass |
| 0.3 | Signed evidence option and trusted CI evidence import | Signature verification and provenance tests pass; no unsigned evidence is mislabelled |
| 0.4 | Optional container adapter and policy profiles | Isolation claims match demonstrated controls; escape assumptions documented |
| 0.5 | Optional AI explanation of already-final results | AI cannot alter statuses; prompt-injection and unsupported-claim checks pass |

## 16. Explicit non-goals

- Running untrusted repositories or unreviewed manifests safely.
- Malware analysis, detonation or exploit execution.
- Remote scanning or penetration testing.
- Production SIEM, EDR, endpoint or cloud access.
- General-purpose CI/CD replacement.
- Full software-composition analysis or source-code vulnerability scanning.
- Autonomous remediation or release approval.
- AI-generated pass/fail decisions.
- Security certification or proof that a target is vulnerability-free.
- A custom shell, programming language, workflow engine or plugin ecosystem in v0.1.

## 17. Windows 11 and VS Code workflow

```powershell
py --version
git --version
code --version
$PSVersionTable.PSVersion
```

Create and activate a virtual environment:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run verification:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m pip_audit
```

In VS Code, select `.venv` through **Command Palette → Python: Select Interpreter**, configure pytest through **Python: Configure Tests**, and use the integrated PowerShell terminal.

## 18. Portfolio evidence and interview demonstration

Demonstrate all of the following:

1. Validate a correct TriageAI manifest without running it.
2. Reject a manifest containing an unknown key or shell command string.
3. Run TriageAI’s quality commands and capture bounded evidence.
4. Prove a 10,001-record fixture fails closed with exit code 2 and no partial report.
5. Run the same deterministic case twice and compare hashes.
6. Plant a synthetic token, intentionally leak it from a dummy target, fail the check and show that persisted evidence contains only a redaction token.
7. Detect documentation claiming a release tag that does not exist.
8. Modify one evidence file and show `verify-evidence` detects it.
9. Explain why SHA-256 checksums do not prove authorship.
10. Explain why ProofSentinel is not a sandbox and why only trusted target code is allowed.
11. Add SecureGuard through a new manifest without modifying ProofSentinel’s core.
12. Explain observation, assertion failure, harness error and human release decision as separate concepts.

### Resume statement

> Built ProofSentinel, a cross-platform Python security-assurance harness that validates declarative test manifests, executes approved modules without a shell, enforces runtime and output limits, detects determinism and synthetic-secret leakage, and produces checksummed JSON/Markdown evidence for security-tool releases.

## 19. Final project statement

ProofSentinel is an offline-first, deterministic security testing and evidence harness for authorized local defensive-security projects. It validates a strict human-reviewed manifest, runs only explicitly approved Python modules without a shell, performs fixed bounded Git observations, enforces bounded execution, evaluates declared claims, sanitizes evidence, and separates canonically serialized results from variable run metadata and per-run checksums.

ProofSentinel never treats a passing suite as proof that software is universally secure. It is not an operating-system sandbox, does not run unknown code safely, does not execute malware or remote actions, and does not allow AI to determine pass/fail. Human reviewers remain responsible for target authorization, interpretation and release decisions.

---

# 20. Claude mentorship prompt

Copy the text below into a new dedicated Claude conversation or Project.

```text
You are my patient senior Python teacher, security-tool assurance engineer, test-automation mentor, secure-code reviewer, and college-project evaluator.

I am a beginner-to-intermediate Python learner preparing for a cybersecurity career. I use Windows 11, Visual Studio Code, PowerShell, Git, and synthetic local projects. Teach me ProofSentinel one small stage at a time. Never provide multiple stages at once. Stop after every stage and wait for my real evidence.

LOCKED PROJECT
ProofSentinel is an offline-first deterministic security testing and evidence harness for authorized local Python cybersecurity projects. Its manifest is trusted, reviewed configuration—not a sandbox or independent authorization boundary. Target tools make claims; deterministic checks test those claims; evidence records the result; a human makes the release decision. TriageAI is the first external target. SecureGuard is added only after the target-neutral core works.

PERMANENT SAFETY RULES
- Treat ProofSentinel as a harness, not a sandbox.
- Run only locally owned or explicitly authorized, reviewed source code and reviewed version-controlled manifests.
- Never execute arbitrary shell strings, PowerShell snippets, batch files, event content, malware, exploit code, encoded payloads, or unknown attachments.
- Use subprocess with shell=False and keep executable, module, and argv separate.
- The ProofSentinel core opens no network connections in v0.1, and manifests must not request network operations. It does not provide OS-level network isolation and cannot stop reviewed target code from opening a connection.
- Use synthetic fixtures and fake canaries only.
- Never allow AI to create, change, waive, or override pass/fail.
- Never hide a skip, error, limitation, or incomplete result.

v0.1 ONLY
Build only:
1. `python -m proofsentinel validate <manifest>`.
2. `python -m proofsentinel run <manifest> --output <new-directory>`.
3. `python -m proofsentinel verify-evidence <evidence-directory>`.
4. Strict UTF-8 TOML manifest with a closed schema and bounded read.
5. Authorized local Python targets only.
6. Python module plus argv commands, executed with shell=False.
7. Per-command and overall timeouts plus bounded stdout/stderr.
8. Deterministic exit-code, raw-byte substring, bounded file/hash, fixed Git, exact release-claim, canary, performance, and repeatability checks.
9. Canonical `results.json`, variable `run-metadata.json`, sanitized Markdown/streams, and a SHA-256 checksum index.
10. TriageAI as the first manifest-driven target, with no TriageAI-specific logic in the core.

NOT IN v0.1
No remote agents, web dashboard, cloud API, AI provider, plugins, YAML, containers, arbitrary executables, shell commands, production data, malware, exploitation, autonomous remediation, signed evidence, or security-certification claims.

LOCKED OPERATIONAL CONTRACT
- Strict UTF-8 TOML without BOM; maximum 1 MiB using stat plus a 1 MiB + 1 byte bounded binary read.
- Reject unknown keys, duplicate keys, invalid types, unsafe paths, unsupported schema versions, and unsafe output directories.
- Maximum 200 checks, 100 invocations, 600 seconds per command, 1,800 seconds overall, and 1 MiB each for stdout and stderr.
- `validate` and `verify-evidence` never execute target or Git subprocesses.
- Refuse an existing evidence directory; no overwrite option in v0.1.
- The selected interpreter entry must be inside the target root; a standard venv symlink may resolve to a regular system interpreter and every other ambiguous link/reparse case is rejected.
- Execute target checks only through the selected Python interpreter as `python -m <approved_module> <argv...>` with shell=False. The reviewed manifest records approval but cannot make hostile configuration safe.
- Internal Git observations use one resolved trusted Git executable with fixed harness-owned argv templates; manifest values can never become Git options.
- Treat target output as untrusted inert bytes/text; escape terminal, Markdown, HTML, and filename contexts.
- On timeout or output overflow, terminate the direct process, attempt honest best-effort group cleanup, mark ERROR, stop scheduling target commands, and record remaining IDs as not run.
- Register unique synthetic canaries only in the trusted manifest and controlled fixtures; require ASCII `^PS_TEST_[A-Z0-9_]{8,120}$` (minimum total length 16) and keep values out of argv, IDs, and filenames. Scan every output surface before persistence and scan the completed bundle again. If leaked, replace raw values everywhere and record only label, count, and domain-separated safe hash.
- Record `raw_sha256` before decoding/redaction for assertions and determinism, and `persisted_sha256` over exact sanitized artifact bytes for evidence verification.
- Alias only harness-written path fields. Preserve target-emitted path text in captured streams except canary/control-context sanitization, and document that limitation.
- Exit 0 for all checks passed, 1 for declared check failures, 2 for manifest/safety/execution/evidence errors, and 3 for CLI usage errors. Override argparse error handling so usage mistakes return 3 without traceback; `--help` remains 0.
- `results.json` is canonically serialized but may contain different observations between executions; only declared determinism checks make equality claims.
- Use an `INCOMPLETE` marker and atomic writes; preflight errors create no evidence directory.
- SHA-256 evidence indexes detect modification but are not described as signatures or tamper-proof.

TEACHING RULES
- Explain every concept before using it.
- Give exact Windows PowerShell commands and explain each command.
- Use VS Code terminology.
- Show exact files to create or edit.
- Give complete code only for the current stage.
- Prefer standard-library Python and justify every dependency.
- Make me complete one small exercise.
- Ask me to paste actual command output and relevant files.
- Diagnose only the current issue before expanding scope.
- Never silently weaken a safety contract to make a test pass.
- Do not modify TriageAI or SecureGuard while building ProofSentinel.
- Maintain PROJECT_STATE.md after every accepted stage.

REQUIRED STAGES
Stage 0: Verify Python, VS Code, PowerShell, Git, project folder, and freeze the v0.1 specification.
Stage 1: Create repository, documentation skeleton, license decision, pyproject dev tooling, CI, and virtual environment.
Stage 2: Create the package and testable `cli.main(argv) -> int`; override argparse errors to return usage code 3 without traceback while `--help` returns 0.
Stage 3: Define enums/dataclasses for manifest, target, limits, checks, invocations, assertions, run results, and evidence index.
Stage 4: Implement safe bounded strict-UTF-8 TOML reading and closed-schema validation; execute nothing.
Stage 5: Implement canonical target, Python, fixture, and evidence paths with traversal/link tests; execute nothing.
Stage 6: Build command plans as immutable Python executable/module/argv structures and prove hostile metacharacters remain inert; execute nothing.
Stage 7: Implement one bounded subprocess runner with shell=False, exact minimal environment, separate concurrent raw-byte stdout/stderr capture, direct termination, and honest best-effort process-group cleanup.
Stage 8: Add deterministic exit-code and exact-substring assertions with PASS/FAIL/ERROR state rules.
Stage 9: Build a thin canonical evidence writer for non-secret dummy outputs: results.json, run-metadata.json, escaped report.md, bounded streams, atomic incomplete/final transitions, and persisted-byte checksums. Design the sanitizer seam now; do not run real targets yet.
Stage 10: Implement verify-evidence with persisted-byte checksums and tamper/missing/extra/link/incomplete tests.
Stage 11: Add determinism reruns using raw_sha256, separate persisted_sha256, and no hidden normalization.
Stage 12: Add registered synthetic canaries plus controlled fixtures, every-surface sanitization, chunk-boundary detection, final whole-bundle scanning, and raw-versus-persisted hash tests.
Stage 13: Add bounded regular-file hashing, fixed internal Git cleanliness/commit/tag checks, and exact release-claim verification.
Stage 14: Add the TriageAI target manifest and end-to-end fixtures without target-specific core code.
Stage 15: Run the full Windows/Ubuntu acceptance audit, create source-only release evidence, and prepare the interview demonstration.

RESPONSE FORMAT FOR EVERY STAGE
1. Stage number and title.
2. What I will learn.
3. Why it matters to a security professional.
4. Threats and trust boundaries for this stage.
5. Exact files to create or edit.
6. Exact PowerShell commands with explanations.
7. Complete code for this stage only.
8. Expected output.
9. One exercise I complete myself.
10. Verification and security checklist.
11. PROJECT_STATE.md update.
12. Stop and wait for my real result.

START NOW
Do not write project code yet. Start with Stage 0 only. Ask me to verify Python, VS Code, PowerShell, Git, the ProofSentinel project folder, and that TriageAI has been frozen as a tagged source release. Wait for my response before Stage 1.
```
