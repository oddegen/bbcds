# ADR 0004: Worker Owns Model Runtime

Status: Accepted for future product work.

The future model runtime belongs in a dedicated module worker. The main thread must not own LiteRT.js inference, preprocessing, compiled model lifecycle, or tensor lifecycle.
