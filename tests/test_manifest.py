"""Tests for manifest reading and validation (Stage 4)."""

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from proofsentinel import manifest as manifest_module
from proofsentinel.manifest import ManifestError, parse_manifest, read_manifest_bytes
from proofsentinel.models import (
    MAX_MANIFEST_BYTES,
    Assertion,
    AssertionKind,
    CheckType,
    Limits,
)

COMMIT_40 = "a" * 40
COMMIT_64 = "b" * 64
CANARY_VALUE = "PS_TEST_API_TOKEN_7K4M2Q9X"

SECTIONS: dict[str, str] = {
    "version": "schema_version = 1\n",
    "target": (
        "[target]\n"
        'name = "Example"\n'
        'root = "../example"\n'
        'python = ".venv/Scripts/python.exe"\n'
        f'expected_git_commit = "{COMMIT_40}"\n'
        "require_clean_git = true\n"
    ),
    "limits": (
        "[limits]\n"
        "command_timeout_seconds = 60\n"
        "overall_timeout_seconds = 1800\n"
        "stdout_bytes = 1048576\n"
        "stderr_bytes = 1048576\n"
    ),
    "modules": '[modules]\nallow = ["examplecli", "pytest"]\n',
    "canaries": f'[canaries]\nfake_api_token = "{CANARY_VALUE}"\n',
    "checks": (
        "[[checks]]\n"
        'id = "quality-pytest"\n'
        'type = "command"\n'
        'module = "pytest"\n'
        'args = ["-q"]\n'
        "expected_exit = 0\n"
        'stdout_contains = ["passed"]\n'
        "\n"
        "[[checks]]\n"
        'id = "deterministic-case"\n'
        'type = "determinism"\n'
        'module = "examplecli"\n'
        'args = ["analyze", "fixtures/case.json"]\n'
        "repetitions = 2\n"
        "\n"
        "[[checks]]\n"
        'id = "record-cap-fails-closed"\n'
        'type = "command"\n'
        'module = "examplecli"\n'
        'args = ["analyze", "fixtures/too-big.json"]\n'
        "expected_exit = 2\n"
        'stdout_exact = ""\n'
        'stderr_contains = ["cap"]\n'
        'canary_labels = ["fake_api_token"]\n'
    ),
}


def make_toml(**changes: str | None) -> str:
    """Join the sections. A value replaces that section; None removes it."""
    unknown = set(changes) - set(SECTIONS)
    assert not unknown, f"unknown section names in test: {unknown}"
    parts = []
    for name, text in SECTIONS.items():
        replacement = changes.get(name, text)
        if replacement is not None:
            parts.append(replacement)
    return "\n".join(parts)


def parse(text: str) -> object:
    return parse_manifest(text.encode("utf-8"))


def mutate_checks(old: str, new: str) -> str:
    """Change one fragment of the checks section, proving the fragment really exists."""
    assert old in SECTIONS["checks"], f"test bug: {old!r} not found in the checks section"
    return make_toml(checks=SECTIONS["checks"].replace(old, new, 1))


def mutate_section(section: str, old: str, new: str) -> str:
    assert old in SECTIONS[section], f"test bug: {old!r} not found in section {section!r}"
    return make_toml(**{section: SECTIONS[section].replace(old, new, 1)})


def determinism_checks(count: int, repetitions: int) -> str:
    return "".join(
        "[[checks]]\n"
        f'id = "repeat-{number}"\n'
        'type = "determinism"\n'
        'module = "pytest"\n'
        f"repetitions = {repetitions}\n\n"
        for number in range(count)
    )


def assert_rejected(text: str | bytes, fragment: str) -> None:
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    with pytest.raises(ManifestError) as excinfo:
        parse_manifest(data)
    assert fragment in str(excinfo.value)


# --- the valid manifest ----------------------------------------------------


def test_valid_manifest_parses_into_models() -> None:
    manifest = parse_manifest(make_toml().encode("utf-8"))
    assert manifest.schema_version == 1
    assert manifest.target.name == "Example"
    assert manifest.target.root == Path("../example")
    assert manifest.target.expected_git_commit == COMMIT_40
    assert manifest.target.require_clean_git is True
    assert manifest.approved_modules == ("examplecli", "pytest")
    assert [check.id for check in manifest.checks] == [
        "quality-pytest",
        "deterministic-case",
        "record-cap-fails-closed",
    ]
    assert manifest.checks[0].type is CheckType.COMMAND
    assert manifest.checks[0].assertions == (
        Assertion(kind=AssertionKind.STDOUT_CONTAINS, expected="passed"),
    )
    assert manifest.checks[1].type is CheckType.DETERMINISM
    assert manifest.checks[1].repetitions == 2
    last = manifest.checks[2]
    assert last.expected_exit == 2
    assert last.canary_labels == ("fake_api_token",)
    assert Assertion(kind=AssertionKind.STDOUT_EXACT, expected="") in last.assertions
    assert Assertion(kind=AssertionKind.STDERR_CONTAINS, expected="cap") in last.assertions
    assert manifest.canaries[0].label == "fake_api_token"


def test_optional_sections_use_safe_defaults() -> None:
    label_line = 'canary_labels = ["fake_api_token"]\n'
    assert label_line in SECTIONS["checks"], "test bug: label line not found"
    checks_without_labels = SECTIONS["checks"].replace(label_line, "")
    text = make_toml(limits=None, canaries=None, checks=checks_without_labels)
    manifest = parse_manifest(text.encode("utf-8"))
    assert manifest.limits == Limits()
    assert manifest.canaries == ()


def test_sixty_four_character_git_object_id_is_accepted() -> None:
    text = mutate_section("target", COMMIT_40, COMMIT_64)
    assert parse_manifest(text.encode("utf-8")).target.expected_git_commit == COMMIT_64


def test_canary_value_never_appears_in_the_parsed_manifest_repr() -> None:
    assert CANARY_VALUE not in repr(parse_manifest(make_toml().encode("utf-8")))


# --- reading ---------------------------------------------------------------


def test_read_returns_the_raw_bytes(tmp_path: Path) -> None:
    path = tmp_path / "manifest.toml"
    data = make_toml().encode("utf-8")
    path.write_bytes(data)
    assert read_manifest_bytes(path) == data


def test_read_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="cannot read manifest"):
        read_manifest_bytes(tmp_path / "missing.toml")


def test_read_rejects_a_directory(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="regular file"):
        read_manifest_bytes(tmp_path)


def test_read_accepts_exactly_the_size_limit(tmp_path: Path) -> None:
    valid = make_toml().encode("utf-8")
    padding = MAX_MANIFEST_BYTES - len(valid) - 2
    data = valid + b"\n#" + b"x" * padding
    assert len(data) == MAX_MANIFEST_BYTES
    path = tmp_path / "manifest.toml"
    path.write_bytes(data)
    assert read_manifest_bytes(path) == data
    assert parse_manifest(data).target.name == "Example"


def test_read_rejects_one_byte_over_the_limit(tmp_path: Path) -> None:
    path = tmp_path / "manifest.toml"
    path.write_bytes(b"#" * (MAX_MANIFEST_BYTES + 1))
    with pytest.raises(ManifestError, match="larger than"):
        read_manifest_bytes(path)


def test_non_regular_file_is_refused_before_it_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipe_like = os.stat_result((stat.S_IFIFO | 0o600, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def refuse_to_open(*args: object, **kwargs: object) -> None:
        raise AssertionError("a non-regular file must not be opened")

    monkeypatch.setattr(
        manifest_module, "os", SimpleNamespace(stat=lambda path: pipe_like, fstat=None)
    )
    monkeypatch.setattr(manifest_module, "open", refuse_to_open, raising=False)
    with pytest.raises(ManifestError, match="regular file"):
        read_manifest_bytes(tmp_path / "anything.toml")


def test_bounded_read_catches_a_file_that_grew_after_the_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "manifest.toml"
    path.write_bytes(b"#" * (MAX_MANIFEST_BYTES + 1))
    # Pretend both stat checks saw a small file, as if it grew after they ran.
    monkeypatch.setattr(manifest_module, "_require_regular_and_small", lambda info: None)
    with pytest.raises(ManifestError, match="larger than"):
        read_manifest_bytes(path)


def test_parse_rejects_oversized_bytes() -> None:
    assert_rejected(b"#" * (MAX_MANIFEST_BYTES + 1), "larger than")


# --- decoding and TOML syntax ----------------------------------------------


@pytest.mark.parametrize(
    "bom",
    [b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"],
    ids=["utf8", "utf16-le", "utf16-be", "utf32-le", "utf32-be"],
)
def test_byte_order_marks_are_rejected(bom: bytes) -> None:
    assert_rejected(bom + make_toml().encode("utf-8"), "byte order mark")


def test_invalid_utf8_is_rejected() -> None:
    assert_rejected(b'name = "\xc3\x28"\n', "not valid UTF-8")


def test_utf16_text_without_a_bom_is_rejected() -> None:
    assert_rejected(make_toml().encode("utf-16-le"), "not valid TOML")


def test_duplicate_keys_are_rejected() -> None:
    assert_rejected(
        mutate_section(
            "version", "schema_version = 1\n", "schema_version = 1\nschema_version = 1\n"
        ),
        "not valid TOML",
    )
    assert_rejected(
        mutate_section("target", 'name = "Example"\n', 'name = "Example"\nname = "Other"\n'),
        "not valid TOML",
    )


def test_invalid_toml_syntax_is_rejected() -> None:
    assert_rejected("this is = = not toml", "not valid TOML")


def test_deeply_nested_arrays_are_rejected_without_crashing() -> None:
    assert_rejected("a = " + "[" * 50_000 + "]" * 50_000, "")


# --- closed schema ---------------------------------------------------------


@pytest.mark.parametrize("section", ["version", "target", "modules", "checks"])
def test_missing_required_top_level_sections_are_rejected(section: str) -> None:
    text = make_toml(**{section: None})
    expected = "schema_version" if section == "version" else section
    assert_rejected(text, f"missing required key '{expected}'")


def test_unknown_top_level_key_is_rejected() -> None:
    assert_rejected(make_toml() + '\nextra = "x"\n', "unknown key 'extra'")


@pytest.mark.parametrize(
    ("section", "addition", "key"),
    [
        ("target", 'color = "red"\n', "color"),
        ("limits", "memory_bytes = 1\n", "memory_bytes"),
        ("modules", 'deny = ["x"]\n', "deny"),
    ],
)
def test_unknown_keys_in_sections_are_rejected(section: str, addition: str, key: str) -> None:
    assert_rejected(make_toml(**{section: SECTIONS[section] + addition}), f"unknown key '{key}'")


def test_unknown_key_in_a_check_is_rejected() -> None:
    assert_rejected(
        mutate_checks('args = ["-q"]\n', 'args = ["-q"]\nshell = true\n'), "unknown key 'shell'"
    )


def test_environment_cannot_be_set_by_a_check() -> None:
    assert_rejected(
        mutate_checks('args = ["-q"]\n', 'args = ["-q"]\nenv = {A = "b"}\n'), "unknown key 'env'"
    )


def test_unknown_key_text_is_escaped_in_errors() -> None:
    text = make_toml() + '\n"bad\\u001bkey" = 1\n'
    with pytest.raises(ManifestError) as excinfo:
        parse_manifest(text.encode("utf-8"))
    assert "\x1b" not in str(excinfo.value)


@pytest.mark.parametrize(
    "version_line",
    ["schema_version = 2\n", "schema_version = 0\n", "schema_version = -1\n"],
)
def test_unsupported_schema_versions_are_rejected(version_line: str) -> None:
    assert_rejected(make_toml(version=version_line), "unsupported version")


@pytest.mark.parametrize(
    "version_line",
    ['schema_version = "1"\n', "schema_version = 1.0\n", "schema_version = true\n"],
)
def test_wrong_types_for_schema_version_are_rejected(version_line: str) -> None:
    assert_rejected(make_toml(version=version_line), "must be an integer")


def test_booleans_are_not_accepted_as_integers() -> None:
    assert_rejected(
        mutate_checks("expected_exit = 0\n", "expected_exit = true\n"), "must be an integer"
    )
    assert_rejected(
        mutate_section("limits", "stdout_bytes = 1048576\n", "stdout_bytes = true\n"),
        "must be an integer",
    )


def test_strings_are_not_accepted_as_integers() -> None:
    assert_rejected(
        mutate_checks("expected_exit = 0\n", 'expected_exit = "0"\n'), "must be an integer"
    )


def test_target_values_are_checked() -> None:
    assert_rejected(
        mutate_section("target", 'name = "Example"', 'name = ""'), "target.name: must not be empty"
    )
    assert_rejected(
        mutate_section("target", 'name = "Example"', "name = 5"), "target.name: must be a string"
    )
    assert_rejected(
        mutate_section("target", "require_clean_git = true", 'require_clean_git = "yes"'),
        "must be true or false",
    )


@pytest.mark.parametrize(
    "commit",
    ["abc1234", "A" * 40, "g" * 40, "a" * 39, "a" * 41, "a" * 63, "a" * 65, "a" * 40 + "\\n"],
    ids=["abbrev", "uppercase", "non-hex", "39", "41", "63", "65", "trailing-newline"],
)
def test_git_object_ids_must_be_full_lowercase_hex(commit: str) -> None:
    text = mutate_section("target", COMMIT_40, commit)
    assert_rejected(text, "target.expected_git_commit")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("command_timeout_seconds = 60", "command_timeout_seconds = 601"),
        ("command_timeout_seconds = 60", "command_timeout_seconds = 0"),
        ("overall_timeout_seconds = 1800", "overall_timeout_seconds = 1801"),
        ("stdout_bytes = 1048576", "stdout_bytes = 1048577"),
        ("stderr_bytes = 1048576", "stderr_bytes = 0"),
    ],
)
def test_limits_cannot_exceed_hard_ceilings(old: str, new: str) -> None:
    assert_rejected(mutate_section("limits", old, new), "limits.")


def test_limits_at_the_ceilings_are_accepted() -> None:
    text = mutate_section("limits", "command_timeout_seconds = 60", "command_timeout_seconds = 600")
    assert parse_manifest(text.encode("utf-8")).limits.command_timeout_seconds == 600


# --- modules ---------------------------------------------------------------


def test_module_list_must_not_be_empty() -> None:
    assert_rejected(make_toml(modules="[modules]\nallow = []\n"), "at least one approved module")


@pytest.mark.parametrize(
    "module",
    ["", "has space", "../escape", "a;b", "1abc", "a..b", "a.b.", "name\\n", "-c"],
)
def test_invalid_module_names_are_rejected(module: str) -> None:
    assert_rejected(make_toml(modules=f'[modules]\nallow = ["{module}"]\n'), "modules.allow[0]")


def test_duplicate_modules_are_rejected() -> None:
    assert_rejected(
        make_toml(modules='[modules]\nallow = ["pytest", "pytest"]\n'), "duplicate module"
    )


def test_dotted_module_names_are_accepted() -> None:
    text = make_toml(modules='[modules]\nallow = ["pkg.sub_module", "examplecli", "pytest"]\n')
    assert "pkg.sub_module" in parse_manifest(text.encode("utf-8")).approved_modules


def test_check_module_must_be_approved() -> None:
    assert_rejected(
        mutate_checks('module = "pytest"', 'module = "pip_audit"'), "not in modules.allow"
    )


# --- canaries --------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "PS_TEST_SHORT",
        "ps_test_api_token_7k4m2q9x",
        "PS_TEST_has-dash_1234",
        "REAL_SECRET_VALUE_1234",
        "PS_TEST_" + "A" * 121,
    ],
)
def test_canary_values_must_match_the_required_pattern(value: str) -> None:
    text = make_toml(canaries=f'[canaries]\nfake_api_token = "{value}"\n')
    with pytest.raises(ManifestError) as excinfo:
        parse_manifest(text.encode("utf-8"))
    assert "canaries.fake_api_token" in str(excinfo.value)
    assert value not in str(excinfo.value)


def test_canary_values_must_be_unique() -> None:
    text = make_toml(canaries=f'[canaries]\none = "{CANARY_VALUE}"\ntwo = "{CANARY_VALUE}"\n')
    assert_rejected(text, "duplicates another canary")


def test_canary_labels_must_be_well_formed() -> None:
    assert_rejected(make_toml(canaries=f'[canaries]\n"Bad Label" = "{CANARY_VALUE}"\n'), "label")


def test_canary_values_cannot_appear_in_arguments() -> None:
    text = mutate_checks('args = ["-q"]', f'args = ["-q", "--token={CANARY_VALUE}"]')
    with pytest.raises(ManifestError) as excinfo:
        parse_manifest(text.encode("utf-8"))
    assert "canary 'fake_api_token'" in str(excinfo.value)
    assert CANARY_VALUE not in str(excinfo.value)


def test_check_canary_labels_must_be_registered() -> None:
    assert_rejected(
        mutate_checks('canary_labels = ["fake_api_token"]', 'canary_labels = ["nope"]'),
        "unknown canary label",
    )


def test_duplicate_check_canary_labels_are_rejected() -> None:
    assert_rejected(
        mutate_checks(
            'canary_labels = ["fake_api_token"]',
            'canary_labels = ["fake_api_token", "fake_api_token"]',
        ),
        "duplicate canary label",
    )


# --- checks ----------------------------------------------------------------


def test_zero_checks_are_rejected() -> None:
    # A top-level key must come before any [table] header, so it goes in the version section.
    text = make_toml(version="schema_version = 1\nchecks = []\n", checks=None)
    assert_rejected(text, "at least one check")


def test_more_than_the_maximum_number_of_checks_is_rejected() -> None:
    many = "".join(
        f'[[checks]]\nid = "check-{number}"\ntype = "command"\nmodule = "pytest"\n\n'
        for number in range(201)
    )
    assert_rejected(make_toml(checks=many), "more than 200 items")


def test_exactly_the_maximum_number_of_checks_is_accepted() -> None:
    many = "".join(
        f'[[checks]]\nid = "check-{number}"\ntype = "command"\nmodule = "pytest"\n\n'
        for number in range(100)
    )
    assert len(parse_manifest(make_toml(checks=many).encode("utf-8")).checks) == 100


@pytest.mark.parametrize(
    "check_id",
    [
        "",
        "Quality",
        "1abc",
        "has_underscore",
        "has.dot",
        "has space",
        "x" * 65,
        "quality-pytest\\n",
        "con",
        "nul",
        "com1",
        "lpt9",
        "aux",
    ],
)
def test_invalid_check_ids_are_rejected(check_id: str) -> None:
    assert_rejected(mutate_checks('id = "quality-pytest"', f'id = "{check_id}"'), "checks[0].id")


def test_sixty_four_character_check_id_is_accepted() -> None:
    check_id = "a" * 64
    text = mutate_checks('id = "quality-pytest"', f'id = "{check_id}"')
    assert parse_manifest(text.encode("utf-8")).checks[0].id == check_id


def test_duplicate_check_ids_are_rejected() -> None:
    assert_rejected(
        mutate_checks('id = "deterministic-case"', 'id = "quality-pytest"'), "duplicate check id"
    )


def test_unknown_check_type_is_rejected() -> None:
    assert_rejected(mutate_checks('type = "command"', 'type = "shell"'), "unknown check type")


@pytest.mark.parametrize("check_type", ["file", "git", "release_claim", "canary", "performance"])
def test_known_but_unimplemented_check_types_are_rejected_not_ignored(check_type: str) -> None:
    text = make_toml(checks=f'[[checks]]\nid = "later"\ntype = "{check_type}"\n')
    assert_rejected(text, "not supported yet")


def test_command_check_cannot_repeat() -> None:
    assert_rejected(
        mutate_checks('args = ["-q"]\n', 'args = ["-q"]\nrepetitions = 2\n'),
        "must be 1 for a command check",
    )


def test_determinism_check_needs_two_repetitions() -> None:
    assert_rejected(mutate_checks("repetitions = 2", "repetitions = 1"), "at least 2 repetitions")


def test_total_invocations_are_capped_after_expanding_repetitions() -> None:
    assert_rejected(make_toml(checks=determinism_checks(5, 21)), "would run 105 invocations")


def test_exactly_the_maximum_total_invocations_is_accepted() -> None:
    manifest = parse_manifest(make_toml(checks=determinism_checks(5, 20)).encode("utf-8"))
    assert len(manifest.checks) == 5


@pytest.mark.parametrize("value", ["-1", "256", "true", '"2"'])
def test_expected_exit_must_be_a_small_integer(value: str) -> None:
    assert_rejected(mutate_checks("expected_exit = 0", f"expected_exit = {value}"), "expected_exit")


def test_check_timeout_cannot_exceed_the_ceiling() -> None:
    assert_rejected(
        mutate_checks('args = ["-q"]\n', 'args = ["-q"]\ntimeout_seconds = 601\n'),
        "timeout_seconds",
    )


def test_empty_contains_assertions_are_rejected() -> None:
    assert_rejected(
        mutate_checks('stdout_contains = ["passed"]', 'stdout_contains = [""]'), "must not be empty"
    )


def test_empty_exact_assertion_is_allowed() -> None:
    manifest = parse_manifest(make_toml().encode("utf-8"))
    assert Assertion(kind=AssertionKind.STDOUT_EXACT, expected="") in manifest.checks[2].assertions


# --- arguments -------------------------------------------------------------


def test_shell_metacharacters_in_arguments_are_kept_as_plain_text() -> None:
    hostile = "; rm -rf / && $(whoami) | `id` > out < in *"
    text = mutate_checks('args = ["-q"]', f'args = ["-q", "{hostile}"]')
    assert parse_manifest(text.encode("utf-8")).checks[0].args == ("-q", hostile)


def test_nul_in_arguments_is_rejected() -> None:
    assert_rejected(mutate_checks('args = ["-q"]', 'args = ["-q", "a\\u0000b"]'), "NUL")


def test_arguments_must_be_a_list_of_strings() -> None:
    assert_rejected(mutate_checks('args = ["-q"]', 'args = "-q"'), "must be a list")
    assert_rejected(mutate_checks('args = ["-q"]', "args = [1]"), "must be a string")


def test_too_many_arguments_are_rejected() -> None:
    items = ", ".join('"x"' for _ in range(129))
    assert_rejected(mutate_checks('args = ["-q"]', f"args = [{items}]"), "more than 128 items")


def test_argument_item_size_limit() -> None:
    assert parse_manifest(
        mutate_checks('args = ["-q"]', f'args = ["{"a" * 4096}"]').encode("utf-8")
    )
    assert_rejected(
        mutate_checks('args = ["-q"]', f'args = ["{"a" * 4097}"]'), "longer than 4096 bytes"
    )


def test_argument_size_limit_counts_utf8_bytes_not_characters() -> None:
    two_byte_characters = "é" * 2049  # 2049 characters, 4098 bytes
    assert_rejected(
        mutate_checks('args = ["-q"]', f'args = ["{two_byte_characters}"]'),
        "longer than 4096 bytes",
    )


def test_total_argument_size_limit() -> None:
    items = ", ".join(f'"{"a" * 4000}"' for _ in range(5))  # 20,000 bytes in total
    assert_rejected(mutate_checks('args = ["-q"]', f"args = [{items}]"), "in total")