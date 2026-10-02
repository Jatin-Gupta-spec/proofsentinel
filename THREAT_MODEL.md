# Threat model

> Skeleton. Each stage adds the threats it addresses.

## Trust boundaries

| Component | Trust |
|---|---|
| Manifest | Trusted, reviewed, version-controlled configuration. Not an authorization boundary. |
| Target code | Trusted and reviewed. Runs with the current user's permissions. |
| Target output | Untrusted bytes and text. Must be treated as inert. |
| Evidence files | Verifiable by checksum; not signed. |

## Threats and status

| Threat | Planned mitigation | Status |
|---|---|---|
| Shell injection through manifest values | `shell=False`; executable, module and argv kept separate | Not implemented |
| Path traversal and links | Canonical path checks, link rejection | Not implemented |
| Resource exhaustion by a target | Timeouts and bounded output | Not implemented |
| Secrets leaking into evidence | Registered synthetic canaries, sanitization, final scan | Not implemented |
| Evidence modification | SHA-256 checksum index (detects change; not a signature) | Not implemented |