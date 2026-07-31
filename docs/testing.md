# Testing

Tests protect behavior and release risk; they do not mirror the source tree.

## Layers

Use the lowest-cost layer that can fail for the right reason:

1. Unit tests for deterministic policy, transformations, and components.
2. Integration tests for repository-owned boundaries such as manifest
   preparation or approval-report generation.
3. Playwright for critical browser journeys, accessibility, and browser-only
   privacy behavior.
4. Protected release checks for real datasets, training, conversion, parity,
   compatibility, and device benchmarks.

Do not repeat the same assertion at every layer. A fast component test and a
browser test may overlap only when they catch different failures.

## Test Quality

- Name the behavior or regression being protected.
- Exercise a stable public boundary and assert observable results.
- Use the smallest deterministic fixture; seed randomness and control time.
- Prefer production code and lightweight boundary fakes over interaction-heavy
  mocks.
- Avoid assertions on source strings, private calls, exact DOM structure,
  generated ordering, timestamps, or incidental counts.
- Security and privacy tests may inspect generated artifacts when execution
  cannot prove that secrets, outputs, or protected references were omitted.
- Delete tests superseded by stronger coverage and keep helpers local until a
  second test genuinely needs them.

## Model Boundaries

Public tests use benign synthetic images and lightweight models. They must not
download datasets or weights, require a GPU, or expose protected paths or raw
probabilities.

Protected workflows verify real data isolation, hashes, grouped splits,
training recovery, held-out metrics, conversion parity, and compatibility.
Public tests verify the code and contracts that enforce those gates.
