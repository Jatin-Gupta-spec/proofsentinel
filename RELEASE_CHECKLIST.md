# Release checklist

Complete every item before tagging a release. Record evidence, not memory.

- [ ] Working tree is clean and the tagged commit is the tested commit
- [ ] pytest, Ruff, strict mypy and pip-audit pass on Windows and Ubuntu (Python 3.11 and 3.13)
- [ ] No required test is silently skipped; every skip is listed with its reason
- [ ] README, LIMITATIONS and CHANGELOG match what the code actually does
- [ ] A clean source archive installs and passes the full suite in a fresh environment
- [ ] Release claims in documentation match a mechanically verified tag and commit