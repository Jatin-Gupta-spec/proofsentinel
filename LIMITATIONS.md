# Limitations

Known limits today and by design. Nothing here is hidden or waived.

- **Not a sandbox.** Target code runs with the current user's permissions. Limits on time and output are harness-level only.
- **No network isolation.** The core opens no connections, but it cannot stop reviewed target code from doing so.
- **Target output may reveal local paths.** Captured streams keep path text that a target prints, apart from required canary and control-character sanitization.
- **Checksums are not signatures.** A SHA-256 index detects modification but does not prove who wrote the evidence.
- **Dependency audit scope.** `pip-audit` checks the environment it runs in, not the project in isolation. In CI, the Python 3.11 runner ships a `setuptools` version flagged by PYSEC-2026-3447, so CI upgrades `pip` and `setuptools` before auditing. The finding was fixed by upgrading, not suppressed, and the audit reflects the upgraded environment.
- **Dependency audit gap.** `pip-audit` cannot audit `proofsentinel` itself because it is not published on PyPI.
- **Symlink tests may skip locally.** The developer's Windows machine cannot currently create symlinks, so tests that need them skip there. They must run in CI before any release.