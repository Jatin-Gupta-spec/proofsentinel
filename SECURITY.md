# Security policy

## Reporting a vulnerability

Please do not report security issues in public issues. Use GitHub's private vulnerability reporting for this repository (Security tab) if it is enabled, or contact the maintainer through their GitHub profile.

## Supported versions

No release exists yet. Only the latest commit on `main` is considered.

## Scope

ProofSentinel is a test harness, not a sandbox. Running a target executes trusted code with the current user's permissions. That is by design and is not, by itself, a vulnerability. Reports about unsafe handling of manifests, paths, output, canaries or evidence integrity are in scope.