# Threat Model

BBCDS is a static, browser-only prototype. The primary assets are user-selected
media, decoded frames, model outputs, protected training evidence, and the
integrity of approved model artifacts.

## Trust Boundaries

- Local media and future direct URLs are untrusted inputs.
- Model artifacts and TensorFlow/LiteRT graphs are executable inputs and are
  trusted only after hash, contract, parity, compatibility, and approval gates.
- Protected datasets, reports, checkpoints, and artifacts stay outside Git and
  temporary storage. Public documentation contains aggregate evidence only.
- Package registries, CI actions, and browser runtimes are supply-chain
  dependencies. Lockfiles, exact runtime versions, immutable action references,
  dependency updates, and review ownership reduce this risk.

## Required Controls

- No media, frame, score, or inference request leaves the browser.
- No uploads, analytics, external inference, backend, or service worker is
  introduced without explicit architecture review.
- Protected outputs use new owner-only paths and never overwrite existing data.
- Release commands validate hashes, source-group isolation, tensor contracts,
  parity gates, runtime compatibility, provenance, and approval identity.
- Browser resources have explicit cleanup paths; compatibility staging is
  local-only and removed after success or failure.

## Out of Scope Today

The current app decodes local files, transfers one frame at a time to a module
worker, samples under fixed bounds, and enforces protected result states. The
worker validates an approved manifest, artifact size, SHA-256, tensor contract,
and output probability contract before operational inference. Missing manifests
select a non-decision demo classifier; invalid configured releases fail closed.

Direct URL handling, artifact release approval, calibrated video-level policy,
cross-browser release coverage, and product performance remain out of scope.
