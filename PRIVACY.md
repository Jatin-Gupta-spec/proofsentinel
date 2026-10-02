# Privacy

> Design intent for v0.1. Each statement becomes a tested claim only when the stage that implements it is complete.

- ProofSentinel's own code is designed to open no network connections and to send no data anywhere.
- Evidence bundles may contain target output. Use synthetic fixtures and fake canaries only; never point it at production data.
- Evidence can reveal local paths printed by a target. See LIMITATIONS.md.
- Development tooling is separate: `pip install` and `pip-audit` use the network during development.