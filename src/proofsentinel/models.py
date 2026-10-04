"""Data definitions for ProofSentinel (Stage 3).

These are plain, immutable data holders. They describe manifests, checks,
results and evidence, but they validate nothing and execute nothing.
Validation arrives in Stage 4: every manifest value must pass through it
before one of these objects is built.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 1

# Hard ceilings from the v0.1 operational contract. Stage 4 enforces them.
MAX_MANIFEST_BYTES: Final = 1024 * 1024
MAX_CHECKS: Final = 200
MAX_INVOCATIONS: Final = 100
DEFAULT_COMMAND_TIMEOUT_SECONDS: Final = 60
MAX_COMMAND_TIMEOUT_SECONDS: Final = 600
MAX_OVERALL_TIMEOUT_SECONDS: Final = 1800
MAX_STREAM_BYTES: Final = 1024 * 1024
MAX_ARGV_ITEMS: Final = 128
MAX_ARGV_ITEM_BYTES: Final = 4096
MAX_ARGV_TOTAL_BYTES: Final = 16 * 1024
MAX_HASHED_FILE_BYTES: Final = 100 * 1024 * 1024


class CheckType(StrEnum):
    """The seven v0.1 check types."""

    COMMAND = "command"
    DETERMINISM = "determinism"
    FILE = "file"
    GIT = "git"
    RELEASE_CLAIM = "release_claim"
    CANARY = "canary"
    PERFORMANCE = "performance"


class CheckStatus(StrEnum):
    """Closed set of check outcomes. v0.1 has no SKIP state."""

    PASS = "PASS"  # noqa: S105 - a status name, not a credential
    FAIL = "FAIL"
    ERROR = "ERROR"


class AssertionKind(StrEnum):
    """What an assertion compares."""

    EXIT_CODE = "exit_code"
    STDOUT_CONTAINS = "stdout_contains"
    STDOUT_EXACT = "stdout_exact"
    STDERR_CONTAINS = "stderr_contains"
    STDERR_EXACT = "stderr_exact"


class GitObjectFormat(StrEnum):
    """Git object ID format of the target repository."""

    SHA1 = "sha1"  # 40-character object IDs
    SHA256 = "sha256"  # 64-character object IDs


class CompletionState(StrEnum):
    """Whether an evidence directory was finished."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class Limits:
    """Per-run resource limits chosen by the manifest (defaults from the contract)."""

    command_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS
    overall_timeout_seconds: int = MAX_OVERALL_TIMEOUT_SECONDS
    stdout_bytes: int = MAX_STREAM_BYTES
    stderr_bytes: int = MAX_STREAM_BYTES


@dataclass(frozen=True, slots=True, kw_only=True)
class TargetDescriptor:
    """The authorized local project under test."""

    name: str
    root: Path
    python_executable: Path
    expected_git_commit: str
    require_clean_git: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class CanaryRegistration:
    """A fake secret registered in the trusted manifest.

    The raw value is hidden from repr() so it cannot leak through logs or
    tracebacks. Never serialize this class with dataclasses.asdict().
    """

    label: str
    value: str = field(repr=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class Assertion:
    """A declared expectation about a command's output."""

    kind: AssertionKind
    expected: int | str


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckDefinition:
    """One check declared in the manifest."""

    id: str
    type: CheckType
    module: str | None = None
    args: tuple[str, ...] = ()
    expected_exit: int = 0
    assertions: tuple[Assertion, ...] = ()
    timeout_seconds: int | None = None
    repetitions: int = 1
    canary_labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Manifest:
    """A complete, already-validated manifest."""

    schema_version: int
    target: TargetDescriptor
    limits: Limits
    approved_modules: tuple[str, ...]
    checks: tuple[CheckDefinition, ...]
    canaries: tuple[CanaryRegistration, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class InvocationResult:
    """Observations from one command invocation."""

    sanitized_command_label: str
    exit_code: int | None  # None when the process produced no exit code
    duration_ms: int
    stdout_size: int
    stderr_size: int
    stdout_raw_sha256: str
    stderr_raw_sha256: str
    stdout_persisted_sha256: str
    stderr_persisted_sha256: str
    timed_out: bool
    output_limited: bool
    sanitized_artifact_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionResult:
    """The outcome of comparing one observation with one declared expectation."""

    kind: AssertionKind
    index: int
    passed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckResult:
    """The outcome of one check."""

    check_id: str
    status: CheckStatus
    assertions: tuple[AssertionResult, ...] = ()
    invocations: tuple[InvocationResult, ...] = ()
    safe_reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Totals:
    """Counts of check outcomes in a run."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    not_run: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalResults:
    """The content of results.json: statuses and hashes, no timings or local paths."""

    schema_version: int
    proofsentinel_version: str
    raw_manifest_sha256: str
    target_revision: str
    git_object_format: GitObjectFormat
    checks: tuple[CheckResult, ...]
    totals: Totals
    overall_status: CheckStatus
    not_run_check_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class RunMetadata:
    """The content of run-metadata.json: measurements that vary between runs."""

    schema_version: int
    proofsentinel_version: str
    completion_state: CompletionState
    inherited_environment_names: tuple[str, ...] = ()
    invocation_durations_ms: tuple[int, ...] = ()
    decoding_replaced_artifacts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceIndexEntry:
    """One line of checksums.sha256."""

    path: str  # relative POSIX path inside the evidence directory
    sha256: str  # lowercase hex of the persisted file bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceIndex:
    """The content of checksums.sha256."""

    entries: tuple[EvidenceIndexEntry, ...] = ()