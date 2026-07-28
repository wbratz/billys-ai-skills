# Security

RLM workflows can read large local corpora and execute model-generated analysis
code. Treat source access, generated code, model credentials, and output
artifacts as security boundaries.

## Report a vulnerability

Please use GitHub’s private vulnerability reporting for this repository. Do not
open a public issue containing exploit details, credentials, or sensitive data.

Include the affected plugin and version, reproduction steps, expected impact,
and any suggested mitigation. You can expect an acknowledgement within seven
days.

## Operating guidance

- Start with dry runs and narrow source scopes.
- Use least-privilege API credentials.
- Review generated code before enabling execution.
- Set explicit cost and recursion limits.
- Do not ingest secrets or regulated data without an approved environment.
