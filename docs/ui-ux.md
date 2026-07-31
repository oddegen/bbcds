# Video Safety-Check UI

This document defines the durable UI safety and accessibility requirements.
Architecture and current implementation status remain authoritative.

## Core Flow

The future workflow is:

1. Choose a local video or supported direct CORS video URL.
2. Show metadata without exposing decoded pixels.
3. Prepare and run local analysis with cancellable progress.
4. Reveal playback only after a safe result, or keep sensitive content covered.
5. Allow removal or a clean restart after completion, cancellation, or failure.

The current shell stops after source selection because no model artifact or
browser inference runtime is bundled.

## Safety Gate

- Before analysis completes, show a neutral protected preview and metadata. Do
  not show frames, thumbnails, or blurred content.
- A safe result may enable playback but must not claim the entire video is
  guaranteed safe.
- A sensitive result pauses and mutes playback, keeps the preview covered, and
  offers removal. Any reveal action requires explicit confirmation.
- Never expose raw class probabilities, stack traces, protected fixture names,
  paths, or URLs in the primary UI.

## Sources and Progress

- Use a native `<input type="file" accept="video/*">` for local selection.
- URL mode supports only direct CORS-enabled video URLs; do not imply support
  for arbitrary pages or streaming sites.
- Show indeterminate progress only before a measurable plan exists. Afterwards,
  report completed/planned samples and bounded phase-aware progress.
- Cancellation stops work, ignores stale responses, releases resources, and
  permits immediate restart. It is not an error.
- Throttle visible progress; decoded frames, bitmaps, tensors, and pixel buffers
  never belong in React state.

## Accessibility

- Controls must work by keyboard, have visible focus, logical order, and touch
  targets near 44 CSS pixels or larger.
- Announce major state changes through an `aria-live` region without announcing
  every frame.
- Do not communicate status by color alone.
- Dialogs trap focus, close with Escape, and restore focus to their trigger.
- Respect reduced motion without weakening concealment or status feedback.
- Support a 320 CSS-pixel viewport without horizontal overflow.

## Performance and Ownership

Worker events flow through an analysis controller into throttled public state;
React renders that state. Decoding, inference, aggregation, and resource
lifecycle do not live in visual components.

UI depends on feature orchestration, which depends on domain contracts and
infrastructure. Domain and worker modules remain independent of React.

Rendered changes require unit coverage for component behavior and Playwright
coverage for the critical browser flow, accessibility, console health, and a
desktop plus mobile viewport when layout can change.
