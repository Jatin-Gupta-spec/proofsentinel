# Project rules

1. ProofSentinel is a harness, not a sandbox.
2. Run only locally owned or explicitly authorized, reviewed code and manifests.
3. Never execute shell strings, PowerShell snippets, batch files, event content, malware, exploit code or encoded payloads.
4. Use `subprocess` with `shell=False`; keep executable, module and argv separate.
5. The core opens no network connections.
6. Use synthetic fixtures and fake canaries only.
7. AI never creates, changes, waives or overrides a pass/fail result.
8. Never hide a skip, error, limitation or incomplete result.
9. Never weaken a safety rule to make a test pass.