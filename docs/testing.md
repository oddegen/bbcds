# Testing

## Current Checks

- Unit tests verify the app renders.
- Playwright verifies the app loads and has no obvious accessibility violations.
- `check:bundle` verifies the built app stays under the initial JS budget.

## Future Product Work

Add deterministic tests for sampling, aggregation, worker stale-response handling, cancellation, accelerator fallback, network privacy assertions, and resource cleanup.

Model baseline tooling should test source-group split isolation, label-order integrity, dataset manifest hashing, training reproducibility metadata, and held-out metric report generation inside the protected process.

Future model release tooling should test real executable behavior: label order, preprocessing parity, Keras-to-TFLite parity, quantization parity, LiteRT compatibility, and browser smoke behavior. Do not add tests that only exercise static schema or interface files.
