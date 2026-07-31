# Security

Report security concerns through a
[private vulnerability report](https://github.com/oddegen/bbcds/security/advisories/new).
Do not disclose suspected vulnerabilities in a public issue. If private
reporting is unavailable, contact the repository owner privately and include
only the minimum reproduction details needed to investigate.

The supported code is the current `main` branch. Security fixes are prioritized
by impact to local-media confidentiality, model or release integrity, and
supply-chain safety; no response-time commitment is currently offered.

Do not add external inference, uploads, telemetry, proxies, service workers, or
cross-origin isolation changes without explicit review. Model assets and
browser ML runtimes require the protected release gates and architecture review.
See the [threat model](docs/threat-model.md) for trust boundaries and controls.
