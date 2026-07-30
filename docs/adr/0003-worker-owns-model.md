# ADR 0003: Worker Owns Model Runtime

Status: Accepted for future product phase.

The future model runtime belongs in a dedicated module worker. The main thread must not own TensorFlow.js inference.
