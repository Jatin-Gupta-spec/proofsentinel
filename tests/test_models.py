"""Tests for the data definitions (Stage 3)."""

import dataclasses
from pathlib import Path

import pytest

from proofsentinel import models
from proofsentinel.models import (
    Assertion,
    AssertionKind,
    AssertionResult,
    CanaryRegistration,
    CanonicalResults,
    CheckDefinition,
    CheckResult,
    CheckStatus,
    CheckType,
    CompletionState,
    EvidenceIndex,
    EvidenceIndexEntry,
    GitObjectFormat,
    InvocationResult,
    Limits,
    Manifest,
    RunMetadata,
    TargetDescriptor,
    Totals,
)

CANARY_VALUE = "PS_TEST_API_TOKEN_7K4M2Q9X"
SHA_A = "a" * 64
SHA_B = "b" * 64


def make_target() -> TargetDescriptor:
    return TargetDescriptor(
        name="Example",
        root=Path("example-target"),
        python_executable=Path("example-target/.venv/python"),
        expected_git_commit="c" * 40,
    )


def make_manifest() -> Manifest:
    return Manifest(
        schema_version=models.SCHEMA_VERSION,
        target=make_target(),
        limits=Limits(),
        approved_modules=("pytest",),
        checks=(
            CheckDefinition(
                id="quality-pytest",
                type=CheckType.COMMAND,
                module="pytest",
                args=("-q",),
                assertions=(Assertion(kind=AssertionKind.STDOUT_CONTAINS, expected="passed"),),
            ),
        ),
        canaries=(CanaryRegistration(label="fake_api_token", value=CANARY_VALUE),),
    )


def make_invocation() -> InvocationResult:
    return InvocationResult(
        sanitized_command_label="pytest -q",
        exit_code=0,
        duration_ms=12,
        stdout_size=10,
        stderr_size=0,
        stdout_raw_sha256=SHA_A,
        stderr_raw_sha256=SHA_B,
        stdout_persisted_sha256=SHA_A,
        stderr_persisted_sha256=SHA_B,
        timed_out=False,
        output_limited=False,
    )


def test_status_set_is_closed_and_has_no_skip() -> None:
    assert {status.value for status in CheckStatus} == {"PASS", "FAIL", "ERROR"}


def test_check_types_match_the_v01_catalogue() -> None:
    assert {check_type.value for check_type in CheckType} == {
        "command",
        "determinism",
        "file",
        "git",
        "release_claim",
        "canary",
        "performance",
    }


def test_git_object_formats_and_completion_states() -> None:
    assert {fmt.value for fmt in GitObjectFormat} == {"sha1", "sha256"}
    assert {state.value for state in CompletionState} == {"complete", "incomplete"}


def test_limit_defaults_and_hard_ceilings_match_the_contract() -> None:
    assert Limits() == Limits(
        command_timeout_seconds=60,
        overall_timeout_seconds=1800,
        stdout_bytes=1_048_576,
        stderr_bytes=1_048_576,
    )
    assert models.MAX_MANIFEST_BYTES == 1_048_576
    assert models.MAX_CHECKS == 200
    assert models.MAX_INVOCATIONS == 100
    assert models.MAX_COMMAND_TIMEOUT_SECONDS == 600
    assert models.MAX_OVERALL_TIMEOUT_SECONDS == 1800
    assert models.MAX_STREAM_BYTES == 1_048_576
    assert models.MAX_ARGV_ITEMS == 128
    assert models.MAX_ARGV_ITEM_BYTES == 4096
    assert models.MAX_ARGV_TOTAL_BYTES == 16 * 1024
    assert models.MAX_HASHED_FILE_BYTES == 100 * 1024 * 1024


def test_defaults_fail_closed() -> None:
    assert make_target().require_clean_git is True
    check = CheckDefinition(id="x", type=CheckType.COMMAND, module="pytest")
    assert check.expected_exit == 0
    assert check.repetitions == 1
    assert check.args == ()


def test_models_are_immutable() -> None:
    manifest = make_manifest()
    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.schema_version = 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.target.name = "Other"


def test_sequences_are_tuples_not_lists() -> None:
    manifest = make_manifest()
    assert isinstance(manifest.approved_modules, tuple)
    assert isinstance(manifest.checks, tuple)
    assert isinstance(manifest.checks[0].args, tuple)
    assert isinstance(manifest.canaries, tuple)


def test_models_reject_positional_arguments() -> None:
    # Positional construction could silently swap the raw and persisted hashes.
    with pytest.raises(TypeError):
        InvocationResult("pytest -q", 0, 12, 10, 0, SHA_A, SHA_B, SHA_A, SHA_B, False, False)


def _model_classes() -> list[type]:
    return [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type)
        and dataclasses.is_dataclass(obj)
        and obj.__module__ == models.__name__
    ]


def test_every_model_class_is_found() -> None:
    assert len(_model_classes()) == 14


@pytest.mark.parametrize("model", _model_classes(), ids=lambda cls: cls.__name__)
def test_every_model_is_frozen_slotted_and_keyword_only(model: type) -> None:
    assert model.__dataclass_params__.frozen
    assert hasattr(model, "__slots__")
    assert all(field.kw_only for field in dataclasses.fields(model))


def test_canary_value_is_hidden_from_repr_and_str() -> None:
    manifest = make_manifest()
    canary = manifest.canaries[0]
    assert canary.value == CANARY_VALUE
    for text in (repr(canary), str(canary), repr(manifest), str(manifest)):
        assert CANARY_VALUE not in text
    assert "fake_api_token" in repr(canary)


def test_full_result_shape_fits_together() -> None:
    check_result = CheckResult(
        check_id="quality-pytest",
        status=CheckStatus.PASS,
        assertions=(AssertionResult(kind=AssertionKind.EXIT_CODE, index=0, passed=True),),
        invocations=(make_invocation(),),
    )
    results = CanonicalResults(
        schema_version=models.SCHEMA_VERSION,
        proofsentinel_version="0.1.0.dev0",
        raw_manifest_sha256=SHA_A,
        target_revision="c" * 40,
        git_object_format=GitObjectFormat.SHA1,
        checks=(check_result,),
        totals=Totals(passed=1),
        overall_status=CheckStatus.PASS,
    )
    metadata = RunMetadata(
        schema_version=models.SCHEMA_VERSION,
        proofsentinel_version="0.1.0.dev0",
        completion_state=CompletionState.COMPLETE,
        invocation_durations_ms=(12,),
    )
    index = EvidenceIndex(entries=(EvidenceIndexEntry(path="results.json", sha256=SHA_A),))
    assert results.not_run_check_ids == ()
    assert results.checks[0].invocations[0].exit_code == 0
    assert metadata.completion_state is CompletionState.COMPLETE
    assert index.entries[0].path == "results.json"
    assert CANARY_VALUE not in repr(results)