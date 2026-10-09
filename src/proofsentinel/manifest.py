"""Safe, bounded loading and strict validation of ProofSentinel manifests (Stage 4).

Nothing here runs a command or inspects the target. Reading is bounded,
decoding is strict UTF-8, the TOML schema is closed (unknown keys are errors)
and every limit from the operational contract is enforced before a Manifest
object exists. The only way to get a Manifest from untrusted text is
parse_manifest().
"""

import os
import re
import stat
import tomllib
from pathlib import Path
from typing import NoReturn

from proofsentinel.models import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    MAX_ARGV_ITEM_BYTES,
    MAX_ARGV_ITEMS,
    MAX_ARGV_TOTAL_BYTES,
    MAX_CHECKS,
    MAX_COMMAND_TIMEOUT_SECONDS,
    MAX_INVOCATIONS,
    MAX_MANIFEST_BYTES,
    MAX_OVERALL_TIMEOUT_SECONDS,
    MAX_STREAM_BYTES,
    SCHEMA_VERSION,
    Assertion,
    AssertionKind,
    CanaryRegistration,
    CheckDefinition,
    CheckType,
    Limits,
    Manifest,
    TargetDescriptor,
)

# Byte order marks: UTF-8, UTF-16 LE (also the start of UTF-32 LE), UTF-16 BE, UTF-32 BE.
_BYTE_ORDER_MARKS = (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")

_CHECK_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
_MODULE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_CANARY_LABEL = re.compile(r"[a-z][a-z0-9_]{0,63}")
_CANARY_VALUE = re.compile(r"PS_TEST_[A-Z0-9_]{8,120}")
_GIT_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")

_WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)

_SUPPORTED_CHECK_TYPES = frozenset({CheckType.COMMAND, CheckType.DETERMINISM})

_MAX_APPROVED_MODULES = 100
_MAX_CANARIES = 64
_MAX_ASSERTIONS_PER_KIND = 64
_MAX_ASSERTION_BYTES = 4096
_MAX_IDENTITY_BYTES = 1024
_MAX_EXIT_CODE = 255


class ManifestError(Exception):
    """The manifest is unsafe, malformed or unsupported. The message is safe to print."""


def _fail(where: str, message: str) -> NoReturn:
    raise ManifestError(f"{where}: {message}")


def _show(value: object, limit: int = 60) -> str:
    """Quote untrusted text so control characters appear as escapes, and shorten it."""
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_manifest_bytes(path: Path) -> bytes:
    """Read a manifest file with a hard size limit. Returns raw bytes; decodes nothing."""
    try:
        # Stat before opening, so a named pipe is refused instead of blocking the open.
        before = os.stat(path)
    except OSError as exc:
        raise ManifestError(f"cannot read manifest: {exc.strerror or 'unknown error'}") from exc
    _require_regular_and_small(before)
    try:
        with open(path, "rb") as handle:
            # Stat the opened file too: the path may have been swapped since the first stat.
            _require_regular_and_small(os.fstat(handle.fileno()))
            data = handle.read(MAX_MANIFEST_BYTES + 1)
    except OSError as exc:
        raise ManifestError(f"cannot read manifest: {exc.strerror or 'unknown error'}") from exc
    if len(data) > MAX_MANIFEST_BYTES:
        _fail("manifest", f"larger than {MAX_MANIFEST_BYTES} bytes")
    return data


def _require_regular_and_small(info: os.stat_result) -> None:
    if not stat.S_ISREG(info.st_mode):
        _fail("manifest", "must be a regular file")
    if info.st_size > MAX_MANIFEST_BYTES:
        _fail("manifest", f"larger than {MAX_MANIFEST_BYTES} bytes")


# ---------------------------------------------------------------------------
# Typed accessors: every one rejects the wrong type instead of converting it
# ---------------------------------------------------------------------------


def _table(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(where, "must be a table")
    return {str(key): item for key, item in value.items()}


def _list(value: object, where: str, *, max_items: int) -> list[object]:
    if not isinstance(value, list):
        _fail(where, "must be a list")
    if len(value) > max_items:
        _fail(where, f"has more than {max_items} items")
    return list(value)


def _str(
    value: object,
    where: str,
    *,
    max_bytes: int,
    allow_empty: bool = False,
    printable_only: bool = False,
) -> str:
    if not isinstance(value, str):
        _fail(where, "must be a string")
    if "\x00" in value:
        _fail(where, "must not contain NUL")
    if not value and not allow_empty:
        _fail(where, "must not be empty")
    if printable_only and not value.isprintable():
        _fail(where, "must not contain control or non-printable characters")
    if len(value.encode("utf-8")) > max_bytes:
        _fail(where, f"is longer than {max_bytes} bytes")
    return value


def _int(value: object, where: str, *, minimum: int, maximum: int) -> int:
    # bool is a subclass of int in Python, so true would otherwise pass as 1.
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(where, "must be an integer")
    if not minimum <= value <= maximum:
        _fail(where, f"must be between {minimum} and {maximum}")
    return value


def _bool(value: object, where: str) -> bool:
    if not isinstance(value, bool):
        _fail(where, "must be true or false")
    return value


def _check_keys(
    table: dict[str, object], where: str, *, required: set[str], optional: set[str]
) -> None:
    unknown = sorted(set(table) - required - optional)
    if unknown:
        _fail(where, f"unknown key {_show(unknown[0])}")
    missing = sorted(required - set(table))
    if missing:
        _fail(where, f"missing required key '{missing[0]}'")


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _parse_target(value: object) -> TargetDescriptor:
    table = _table(value, "target")
    _check_keys(
        table,
        "target",
        required={"name", "root", "python", "expected_git_commit"},
        optional={"require_clean_git"},
    )
    name = _str(table["name"], "target.name", max_bytes=128, printable_only=True)
    root = _str(table["root"], "target.root", max_bytes=_MAX_IDENTITY_BYTES, printable_only=True)
    python = _str(
        table["python"], "target.python", max_bytes=_MAX_IDENTITY_BYTES, printable_only=True
    )
    commit = _str(table["expected_git_commit"], "target.expected_git_commit", max_bytes=64)
    if not _GIT_OBJECT_ID.fullmatch(commit):
        _fail(
            "target.expected_git_commit",
            "must be a full 40- or 64-character lowercase hexadecimal Git object ID",
        )
    require_clean = _bool(table.get("require_clean_git", True), "target.require_clean_git")
    return TargetDescriptor(
        name=name,
        root=Path(root),
        python_executable=Path(python),
        expected_git_commit=commit,
        require_clean_git=require_clean,
    )


def _parse_limits(value: object | None) -> Limits:
    if value is None:
        return Limits()
    table = _table(value, "limits")
    _check_keys(
        table,
        "limits",
        required=set(),
        optional={
            "command_timeout_seconds",
            "overall_timeout_seconds",
            "stdout_bytes",
            "stderr_bytes",
        },
    )
    return Limits(
        command_timeout_seconds=_int(
            table.get("command_timeout_seconds", DEFAULT_COMMAND_TIMEOUT_SECONDS),
            "limits.command_timeout_seconds",
            minimum=1,
            maximum=MAX_COMMAND_TIMEOUT_SECONDS,
        ),
        overall_timeout_seconds=_int(
            table.get("overall_timeout_seconds", MAX_OVERALL_TIMEOUT_SECONDS),
            "limits.overall_timeout_seconds",
            minimum=1,
            maximum=MAX_OVERALL_TIMEOUT_SECONDS,
        ),
        stdout_bytes=_int(
            table.get("stdout_bytes", MAX_STREAM_BYTES),
            "limits.stdout_bytes",
            minimum=1,
            maximum=MAX_STREAM_BYTES,
        ),
        stderr_bytes=_int(
            table.get("stderr_bytes", MAX_STREAM_BYTES),
            "limits.stderr_bytes",
            minimum=1,
            maximum=MAX_STREAM_BYTES,
        ),
    )


def _parse_modules(value: object) -> tuple[str, ...]:
    table = _table(value, "modules")
    _check_keys(table, "modules", required={"allow"}, optional=set())
    items = _list(table["allow"], "modules.allow", max_items=_MAX_APPROVED_MODULES)
    if not items:
        _fail("modules.allow", "must list at least one approved module")
    modules: list[str] = []
    for index, item in enumerate(items):
        where = f"modules.allow[{index}]"
        module = _str(item, where, max_bytes=255)
        if not _MODULE_NAME.fullmatch(module):
            _fail(where, f"{_show(module)} is not a valid Python module name")
        if module in modules:
            _fail(where, f"duplicate module {_show(module)}")
        modules.append(module)
    return tuple(modules)


def _parse_canaries(value: object | None) -> tuple[CanaryRegistration, ...]:
    if value is None:
        return ()
    table = _table(value, "canaries")
    if len(table) > _MAX_CANARIES:
        _fail("canaries", f"has more than {_MAX_CANARIES} entries")
    registrations: list[CanaryRegistration] = []
    seen_values: set[str] = set()
    for label, raw_value in table.items():
        if not _CANARY_LABEL.fullmatch(label):
            _fail("canaries", f"label {_show(label)} must match [a-z][a-z0-9_]{{0,63}}")
        where = f"canaries.{label}"
        # Error messages below never include the value: a mistaken real secret must not be echoed.
        text = _str(raw_value, where, max_bytes=128)
        if not _CANARY_VALUE.fullmatch(text):
            _fail(where, "value must match PS_TEST_ followed by 8 to 120 of A-Z, 0-9 or _")
        if text in seen_values:
            _fail(where, "value duplicates another canary")
        seen_values.add(text)
        registrations.append(CanaryRegistration(label=label, value=text))
    return tuple(registrations)


def _parse_check_type(value: object, where: str) -> CheckType:
    text = _str(value, where, max_bytes=64, printable_only=True)
    try:
        check_type = CheckType(text)
    except ValueError:
        _fail(where, f"unknown check type {_show(text)}")
    if check_type not in _SUPPORTED_CHECK_TYPES:
        _fail(where, f"check type '{check_type.value}' is not supported yet in this version")
    return check_type


def _parse_check(
    value: object,
    index: int,
    *,
    approved_modules: tuple[str, ...],
    canaries: tuple[CanaryRegistration, ...],
) -> CheckDefinition:
    where = f"checks[{index}]"
    table = _table(value, where)
    if "type" not in table:
        _fail(where, "missing required key 'type'")
    check_type = _parse_check_type(table["type"], f"{where}.type")
    _check_keys(
        table,
        where,
        required={"id", "type", "module"},
        optional={
            "args",
            "expected_exit",
            "stdout_contains",
            "stdout_exact",
            "stderr_contains",
            "stderr_exact",
            "timeout_seconds",
            "repetitions",
            "canary_labels",
        },
    )

    check_id = _str(table["id"], f"{where}.id", max_bytes=64)
    if not _CHECK_ID.fullmatch(check_id):
        _fail(f"{where}.id", f"{_show(check_id)} must match [a-z][a-z0-9-]{{0,63}}")
    if check_id in _WINDOWS_RESERVED_NAMES:
        _fail(f"{where}.id", f"{_show(check_id)} is a reserved Windows device name")

    module = _str(table["module"], f"{where}.module", max_bytes=255)
    if not _MODULE_NAME.fullmatch(module):
        _fail(f"{where}.module", f"{_show(module)} is not a valid Python module name")
    if module not in approved_modules:
        _fail(f"{where}.module", f"{_show(module)} is not in modules.allow")

    args = _parse_args(table.get("args", []), f"{where}.args", canaries)
    expected_exit = _int(
        table.get("expected_exit", 0),
        f"{where}.expected_exit",
        minimum=0,
        maximum=_MAX_EXIT_CODE,
    )

    assertions: list[Assertion] = []
    for key, kind in (
        ("stdout_contains", AssertionKind.STDOUT_CONTAINS),
        ("stderr_contains", AssertionKind.STDERR_CONTAINS),
    ):
        for position, item in enumerate(
            _list(table.get(key, []), f"{where}.{key}", max_items=_MAX_ASSERTIONS_PER_KIND)
        ):
            # An empty needle is contained in every output, so it would always pass.
            text = _str(item, f"{where}.{key}[{position}]", max_bytes=_MAX_ASSERTION_BYTES)
            assertions.append(Assertion(kind=kind, expected=text))
    for key, kind in (
        ("stdout_exact", AssertionKind.STDOUT_EXACT),
        ("stderr_exact", AssertionKind.STDERR_EXACT),
    ):
        if key in table:
            text = _str(
                table[key], f"{where}.{key}", max_bytes=_MAX_ASSERTION_BYTES, allow_empty=True
            )
            assertions.append(Assertion(kind=kind, expected=text))

    timeout_seconds: int | None = None
    if "timeout_seconds" in table:
        timeout_seconds = _int(
            table["timeout_seconds"],
            f"{where}.timeout_seconds",
            minimum=1,
            maximum=MAX_COMMAND_TIMEOUT_SECONDS,
        )

    repetitions = _int(
        table.get("repetitions", 1),
        f"{where}.repetitions",
        minimum=1,
        maximum=MAX_INVOCATIONS,
    )
    if check_type is CheckType.COMMAND and repetitions != 1:
        _fail(f"{where}.repetitions", "must be 1 for a command check; use a determinism check")
    if check_type is CheckType.DETERMINISM and repetitions < 2:
        _fail(f"{where}.repetitions", "a determinism check needs at least 2 repetitions")

    canary_labels = _parse_canary_labels(
        table.get("canary_labels", []), f"{where}.canary_labels", canaries
    )

    return CheckDefinition(
        id=check_id,
        type=check_type,
        module=module,
        args=args,
        expected_exit=expected_exit,
        assertions=tuple(assertions),
        timeout_seconds=timeout_seconds,
        repetitions=repetitions,
        canary_labels=canary_labels,
    )


def _parse_args(
    value: object, where: str, canaries: tuple[CanaryRegistration, ...]
) -> tuple[str, ...]:
    items = _list(value, where, max_items=MAX_ARGV_ITEMS)
    args: list[str] = []
    total_bytes = 0
    for index, item in enumerate(items):
        text = _str(item, f"{where}[{index}]", max_bytes=MAX_ARGV_ITEM_BYTES, allow_empty=True)
        total_bytes += len(text.encode("utf-8"))
        for canary in canaries:
            if canary.value in text:
                _fail(f"{where}[{index}]", f"contains the value of canary '{canary.label}'")
        args.append(text)
    if total_bytes > MAX_ARGV_TOTAL_BYTES:
        _fail(where, f"is longer than {MAX_ARGV_TOTAL_BYTES} bytes in total")
    return tuple(args)


def _parse_canary_labels(
    value: object, where: str, canaries: tuple[CanaryRegistration, ...]
) -> tuple[str, ...]:
    known = {canary.label for canary in canaries}
    labels: list[str] = []
    for index, item in enumerate(_list(value, where, max_items=_MAX_CANARIES)):
        label = _str(item, f"{where}[{index}]", max_bytes=64, printable_only=True)
        if label not in known:
            _fail(f"{where}[{index}]", f"unknown canary label {_show(label)}")
        if label in labels:
            _fail(f"{where}[{index}]", f"duplicate canary label {_show(label)}")
        labels.append(label)
    return tuple(labels)


def _invocation_count(check: CheckDefinition) -> int:
    return check.repetitions if check.type is CheckType.DETERMINISM else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_manifest(data: bytes) -> Manifest:
    """Validate raw manifest bytes and build a Manifest. Raises ManifestError on any problem.

    Read the file once with read_manifest_bytes(), hash those bytes if needed,
    and pass the same bytes here, so the hash and the parsed content always match.
    """
    if len(data) > MAX_MANIFEST_BYTES:
        _fail("manifest", f"larger than {MAX_MANIFEST_BYTES} bytes")
    if data.startswith(_BYTE_ORDER_MARKS):
        _fail("manifest", "must be UTF-8 without a byte order mark")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _fail("manifest", "is not valid UTF-8")
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        _fail("manifest", f"is not valid TOML ({_show(str(exc), 200)})")
    except RecursionError:
        _fail("manifest", "is nested too deeply")

    root = _table(raw, "manifest")
    _check_keys(
        root,
        "manifest",
        required={"schema_version", "target", "modules", "checks"},
        optional={"limits", "canaries"},
    )

    version = root["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        _fail("schema_version", "must be an integer")
    if version != SCHEMA_VERSION:
        _fail(
            "schema_version",
            f"unsupported version {version}; this version supports {SCHEMA_VERSION}",
        )

    target = _parse_target(root["target"])
    limits = _parse_limits(root.get("limits"))
    approved_modules = _parse_modules(root["modules"])
    canaries = _parse_canaries(root.get("canaries"))

    items = _list(root["checks"], "checks", max_items=MAX_CHECKS)
    if not items:
        # Zero checks would "pass" while proving nothing.
        _fail("checks", "must declare at least one check")
    checks = tuple(
        _parse_check(item, index, approved_modules=approved_modules, canaries=canaries)
        for index, item in enumerate(items)
    )

    seen_ids: set[str] = set()
    for index, check in enumerate(checks):
        if check.id in seen_ids:
            _fail(f"checks[{index}].id", f"duplicate check id {_show(check.id)}")
        seen_ids.add(check.id)

    planned = sum(_invocation_count(check) for check in checks)
    if planned > MAX_INVOCATIONS:
        _fail("checks", f"would run {planned} invocations; the maximum is {MAX_INVOCATIONS}")

    return Manifest(
        schema_version=version,
        target=target,
        limits=limits,
        approved_modules=approved_modules,
        checks=checks,
        canaries=canaries,
    )