# Privacy

The planned product is browser-only. Content must not leave the browser for inference.

Current browser-flow status:

- Local files are decoded and sampled in the browser under fixed limits.
- Frames move one at a time to a module worker and are never stored in React
  state, logs, reports, or network requests.
- No model assets are committed. A missing approved local model activates a
  non-decision demo flow that keeps playback covered.
- No analytics or telemetry exists.
- No backend exists.

Future benchmark exports must omit source filenames and URLs by default.
