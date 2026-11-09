# Evidence Packages

Each evaluation run must produce a self-contained evidence package. This directory must never contain real credentials, personal data, payment-card data or unapproved partner material.

## Recommended layout

```text
evidence/
  <run-id>/
    authorization/
    inputs/
    manifests/
    predictions/
    evaluation/
    review/
    limitations.md
```

Partner evidence should remain private unless publication is explicitly authorized. Public packages must use synthetic or approved sanitized data.

## Required manifest fields

- run ID and claim level;
- repository commit;
- protocol version and hash;
- dataset or case hash;
- model and detector versions;
- baseline definition;
- random seed, when applicable;
- execution environment;
- start and end timestamps;
- threshold source;
- primary endpoint;
- denominators;
- cost and token usage, when applicable;
- deviations;
- artifact hashes.

## Claim status values

- `development_only`
- `integration_only`
- `reproducibility_only`
- `independently_reproduced`
- `retrospective_external_pilot`
- `authorized_shadow`

No package may be promoted to a stronger status after inspecting results unless the requirements of the stronger gate were satisfied before execution.
