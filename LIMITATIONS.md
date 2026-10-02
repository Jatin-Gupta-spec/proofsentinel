# Limitations

Known limits today and by design. Nothing here is hidden or waived.

- **Not a sandbox.** Target code runs with the current user's permissions. Limits on time and output are harness-level only.
- **No network isolation.** The core opens no connections, but it cannot stop reviewed target code from doing so.
- **Target output may reveal local paths.** Captured streams keep path text that a target prints, apart from required canary and control-character sanitization.
- **Checksums are not signatures.** A SHA-256 index detects modification but does not prove who wrote the evidence.
- **Dependency audit gap.** `pip-audit` cannot audit `proofsentinel` itself because it is not published on PyPI.
- **Symlink tests may skip locally.** The developer's Windows machine cannot currently create symlinks, so tests that need them skip there. They must run in CI before any release.