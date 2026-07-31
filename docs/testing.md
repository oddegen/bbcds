# Testing

Tests protect behavior and release risk. They are not a mirror of the source
tree and coverage percentage is not a reason by itself to add a test.

## Test Selection

Use the lowest-cost layer that can fail for the right reason:

1. Unit tests for deterministic policy, transformation, and component behavior.
2. Integration tests for boundaries owned by this repository, such as manifest
   preparation through validation or evidence writing through schema checking.
3. Browser tests for critical user journeys, accessibility, runtime errors, and
   browser-only privacy behavior.
4. Protected release checks for full training, real datasets, model conversion,
   compatibility, parity, and device benchmarks.

Do not repeat the same assertion at every layer. Some overlap is acceptable
when each layer catches a distinct failure mode, such as a fast component test
and a real-browser accessibility check.

## Quality Rules

- Name the behavior or regression being protected.
- Exercise stable public boundaries and assert observable results.
- Keep tests deterministic, independent, order-insensitive, and free of remote
  network dependencies.
- Use the smallest realistic fixture. Prefer production code and lightweight
  fakes over interaction-heavy mocks.
- Seed randomness and use explicit tolerances for floating-point results.
- Avoid assertions on private calls, source strings, exact DOM structure,
  generated ordering, cell counts, timestamps, or timing unless they are part
  of an accepted contract.
- A test must fail when its protected behavior breaks. Delete or rewrite tests
  that only restate implementation or duplicate stronger coverage.
- Security and privacy assertions may inspect generated artifacts when runtime
  execution cannot prove that credentials, outputs, or protected references
  were omitted.

## Agent Workflow

For every implementation change:

1. Identify the observable behavior, regression risk, and accepted contract.
2. Search the existing suite before creating a new file or test.
3. Choose the lowest-cost layer that proves the behavior through a stable
   boundary.
4. For defect fixes, confirm the new or changed test fails without the fix when
   practical.
5. Run the focused test while iterating, then the required package and
   repository checks.
6. Remove superseded, duplicate, or implementation-coupled tests.
7. Report what risk is protected, what was not run, and any remaining
   environment-dependent validation.

Do not create test plans, fixture frameworks, helper modules, snapshots, or
custom commands until repeated use demonstrates that they reduce maintenance.
Keep test-only abstractions local to one file until another test genuinely
needs them.

These rules follow Codex's documented use of
[`AGENTS.md` for durable repository expectations](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md),
Google's guidance to
[test behavior rather than implementation](https://testing.googleblog.com/2013/08/testing-on-toilet-test-behavior-not.html),
Testing Library's
[user-centered guiding principles](https://testing-library.com/docs/guiding-principles/),
pytest's [integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html),
and TensorFlow's
[deterministic testing guidance](https://www.tensorflow.org/community/contribute/tests).

## Current Checks

- Vitest verifies the React shell through accessible roles.
- Playwright verifies the real browser shell and automated accessibility scan.
- `check:bundle` enforces the initial JavaScript budget.
- Pytest verifies model policy logic, protected manifest behavior, evidence
  privacy, checkpoint recovery, and the generated notebook's security gates.

## Model Boundaries

Pull-request tests use benign synthetic images and lightweight models. They
must not download datasets or pretrained weights, require a GPU, expose
protected paths, or store raw probabilities.

The protected training workflow verifies source isolation, image and manifest
hashes, deterministic grouped splits, resumable checkpoints, held-out metrics,
and schema-valid aggregate evidence.

Future model release tooling must verify executable label order, preprocessing
parity, Keras-to-TFLite parity, quantization parity, LiteRT compatibility, and
browser inference. Static schema or interface-file tests do not substitute for
those checks.
