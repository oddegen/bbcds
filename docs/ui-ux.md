# Implement the video safety-check UI

This page defines the user interface requirements for future video safety-check work. Use it when implementing the browser UI, reviewing interaction changes, or validating rendered behavior.

## What this page covers

This page covers the product-facing interface for selecting a video, analyzing it locally, showing progress, and gating playback until the safety decision allows it.

It does not define model scope, sampling policy, runtime choice, worker protocol, or mutable implementation status. Those remain in:

- `ARCHITECTURE.md`
- `docs/implementation-status.md`
- `docs/adr`
- `docs/testing.md`

## Source of truth

Treat this page as implementation guidance, not the source of truth for architecture or current status.

Check `docs/implementation-status.md` before assuming any product milestone exists. As of the current status, the browser detection pipeline, worker inference, adaptive sampling, direct Cross-Origin Resource Sharing (CORS) URL mode, playback restriction, and benchmark collection are pending.

Follow accepted Architecture Decision Records (ADRs) before this page when they conflict. In particular:

- Inference must stay browser-only
- The baseline must not require cross-origin isolation
- Confidence is a heuristic until calibration evidence exists
- Worker communication must reject stale scan or request responses
- The scan pipeline must clean up workers, object URLs, frames, tensors, timers, and abort controllers

## Design principles

Design the interface as a calm utility for a single task: checking whether a selected video can be revealed.

Prioritize requirements in this order:

1. Prevent premature exposure to unsafe content
2. Keep video processing local to the device
3. Protect mobile performance, memory, and battery life
4. Communicate clearly and accessibly
5. Preserve correct state, cancellation, and stale-response behavior
6. Support target browsers
7. Add visual polish
8. Add decorative motion

Do not trade safety, privacy, responsiveness, accessibility, or cancellation for a more elaborate visual treatment.

The interface should not look like an artificial intelligence dashboard, security console, media editor, analytics product, or marketing page. Use one centered workflow, one primary action per state, restrained status colors, and short nonjudgmental copy.

## Required flow

The primary journey must support this sequence:

1. The application loads
2. The empty state renders
3. The user selects **File** or **Video URL**
4. The user selects a local video or enters a supported direct CORS video URL
5. The selected-video state renders without exposing a decoded frame
6. The user starts analysis
7. The preparing state renders
8. Determinate progress renders after a measurable scan plan exists
9. Optional refinement renders when the controller checks a suspicious section
10. The final safe or sensitive result renders
11. The user plays, removes, reveals, or starts another analysis

Errors must stay recoverable. Cancellation must be available during preparation, analysis, and refinement unless a future ADR documents a critical operation that cannot be interrupted.

## UI states

Model the interface as explicit states rather than unrelated loading booleans.

Use this public UI state shape unless implementation evidence requires a narrower contract:

```typescript
type UiState =
  | 'idle'
  | 'source-selected'
  | 'preparing'
  | 'analyzing'
  | 'refining'
  | 'completed-safe'
  | 'completed-inappropriate'
  | 'cancelled'
  | 'error'
```

Each state must define:

- A title
- Supporting text
- One primary action
- Valid secondary actions
- An accessible status announcement
- Valid transitions to the next state

Do not leave stale actions visible from previous states.

## Safety gate

The safety gate controls when real video pixels may be shown.

Before analysis completes, use a protected preview surface. Show a neutral placeholder, file metadata, and status text. Do not show the first frame, sampled frames, thumbnail timelines, or weakly blurred unsafe content.

When the result is safe:

- Allow playback
- Remove the protective cover
- Show a calm success result
- Present confidence as secondary heuristic information
- State how many frames were analyzed

Use copy such as:

```text
No inappropriate content detected
```

Do not say the video is completely safe. The product samples frames and cannot guarantee every frame was inspected.

When sensitive content is detected:

- Pause the video
- Mute the video
- Keep the preview covered
- Prevent automatic playback
- Show a direct nonjudgmental warning
- Provide **Remove video**
- Provide **Show anyway** only when product policy allows it

Use copy such as:

```text
Sensitive content detected
```

If reveal is available, use a confirmation dialog with a title, a direct warning, **Keep hidden** as the safe action, and **Reveal video** as the confirmation action.

## Source selection

Use a two-option segmented control:

```text
File | Video URL
```

The **File** path must use a native `<input type="file" accept="video/*">`. Make the selection area tappable, include a visible button, and support drag and drop on desktop as an enhancement. Do not depend on drag and drop for mobile.

Use file-selection language. Do not say "uploading" unless a future architecture change adds an upload path.

The **Video URL** path must only claim support for direct CORS-enabled video URLs. Do not claim support for arbitrary web pages, YouTube URLs, social media URLs, or streaming pages.

Use copy such as:

```text
Enter a direct video URL. The host must allow browser access.
```

After selection, show one selected-video card with:

- Filename or URL host
- Duration when available
- File size for local files
- Resolution when available
- **Change** or **Remove**
- **Analyze video**

The primary action must be full width on narrow mobile viewports and at least 48 CSS pixels high.

## Progress and cancellation

Use **Preparing analysis** while the app loads the model, checks browser support, reads metadata, or creates the sampling plan. Show an indeterminate spinner only during work without a measurable denominator.

Use determinate progress after the scan plan exists. Display:

- Stage title
- Completed sample count
- Planned sample count
- Percentage
- Progress bar
- **Cancel**

Use copy such as:

```text
Analyzing on this device
Checking frame 28 of 72
```

Progress must represent completed planned work. It must not move backward during normal operation. If refinement adds bounded work, adjust progress with a phase-aware calculation so the visible percentage does not suddenly drop.

Throttle visible progress updates to 4 to 8 updates per second. Keep high-frequency worker values in refs or runtime state outside React rendering.

When cancelled:

- Stop the active scan
- Ignore stale worker responses
- Release temporary resources
- Show a cancelled state
- Allow immediate restart

Use copy such as:

```text
Analysis cancelled
The selected video was not fully checked.
```

Do not treat cancellation as an error.

## Results and errors

Result panels must summarize the decision without overclaiming.

For safe results, show:

- Playable video
- **No inappropriate content detected**
- Confidence as secondary information
- Frames analyzed
- **Play video**
- **New analysis**

For sensitive results, show:

- Protected preview
- **Sensitive content detected**
- Confidence as secondary information
- Frames analyzed
- **Remove video**
- Optional **Show anyway**

Errors must render inside the workflow card. Each error must include a clear title, one sentence of explanation, a recovery action, and optional collapsed technical details.

Cover at least these error cases:

- Unsupported or unreadable video
- CORS-blocked URL
- Model failed to load
- Browser runtime unsupported
- Video decode failed
- Analysis timed out
- Worker terminated unexpectedly
- Memory or resource failure
- User cancelled

Use clear recovery copy:

```text
We could not read this video
The file format or codec may not be supported by this browser.
```

Do not show raw stack traces, tensor names, browser exceptions, internal error objects, local paths, frame pixels, filenames from protected fixtures, URLs from protected fixtures, or class probabilities in the primary UI.

## Accessibility

Accessibility is part of completion.

All interactive controls must support keyboard operation, visible focus, logical focus order, and target sizes of about 44 by 44 CSS pixels or larger.

The file input must remain accessible through its label. The source selector must support keyboard navigation. Dialogs must close with Escape, trap focus while open, and return focus to the triggering action.

Use an `aria-live` region for major state changes:

- Video selected
- Analysis started
- Analysis 25 percent complete
- Analysis 50 percent complete
- Analysis 75 percent complete
- Additional frames are being checked
- No inappropriate content detected
- Sensitive content detected
- Analysis cancelled
- Analysis failed

Do not announce progress on every frame.

The progress element must have an accessible label, minimum, maximum, current value, and nearby status text.

Do not communicate state by color alone. Pair status color with text and an icon.

Respect reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  /* Remove nonessential transitions and transforms. */
}
```

Reduced-motion mode must preserve immediate state communication and safety-related concealment.

## Performance boundaries

The UI must stay subordinate to video decoding and inference.

Do not:

- Update React state for every worker message
- Store decoded frames, `ImageBitmap` objects, tensors, canvases, or pixel buffers in React state
- Create thumbnails for every sample
- Re-render the whole page on progress changes
- Recreate the video element between minor state transitions
- Mount multiple video elements for decorative previews
- Calculate expensive diagnostics during render
- Let UI animation delay cancellation

Use this event path:

```text
Worker events
analysis controller
throttled public progress snapshot
React state
progress component
```

Keep the worker, model session, decoder, and sampling scheduler independent from React rendering.

## Component architecture

Separate generic user interface primitives from product-specific video components.

Use this dependency direction:

- UI components depend on feature orchestration and shared UI
- Feature orchestration depends on domain contracts and infrastructure clients
- Domain logic does not import React, Document Object Model (DOM) APIs, LiteRT.js, workers, or browser globals
- Worker code does not import React or UI modules

Use these product components when the feature implementation starts:

- `video-moderation-screen`
- `video-source-selector`
- `video-file-picker`
- `video-url-form`
- `selected-video-card`
- `protected-video-preview`
- `scan-progress-panel`
- `safe-result-panel`
- `sensitive-result-panel`
- `analysis-error-panel`
- `technical-details`

Do not define React components inside other React components. Do not place worker, decoding, inference, or aggregation logic inside visual components.

If shadcn/ui is added later, inspect the project configuration first. Confirm `components.json`, package manager, aliases, Tailwind setup, primitive base, and icon library before adding or overwriting components. Use existing configured primitives before building generic substitutes, and preserve local modifications.

Map generic primitives this way when they exist:

- Primary and secondary actions: button
- File and URL selector: segmented control or toggle group
- Workflow container: card
- Progress: progress
- Warnings and errors: alert
- Reveal confirmation: alert dialog
- Technical details: collapsible
- Status labels: badge
- Empty file-selection state: empty state
- Loading: spinner

Use semantic design tokens in feature components. Do not spread raw color classes through product components.

## Copy standards

Write direct, calm, nontechnical copy. Use sentence case.

Use:

```text
Video safety check
Runs privately on this device
Analyze video
Preparing analysis
Analyzing on this device
Checking a suspicious section
No inappropriate content detected
Sensitive content detected
Preview hidden
Choose another video
New analysis
```

Avoid:

```text
Run AI inference
Execute MobileNet
GPU backend active
AI found pornography
Dangerous content
100% safe
Uploading video
```

Privacy copy must be accurate. Prefer:

```text
Your video is analyzed locally and is not uploaded for processing.
```

Do not claim nothing ever leaves the device if the app loads remote assets, accepts remote URLs, sends telemetry, or later adds any external request path.

## Validation checklist

Before handoff for UI implementation, verify:

- The empty state explains the task
- File selection works through the native picker
- Supported URL mode does not overclaim browser access
- Selected video metadata renders without showing a frame
- Analysis can start and cancel
- Progress is determinate after the plan exists
- Progress does not move backward during refinement
- Safe playback is enabled only after the safety gate
- Sensitive results remain covered
- Reveal uses a confirmation dialog when available
- Error states include recovery actions
- A second analysis starts cleanly
- Keyboard operation works
- Focus is visible and managed through dialogs
- Important states are announced without noisy frame-by-frame updates
- Touch targets work at 320 CSS pixels wide
- No horizontal overflow appears on mobile
- Reduced motion removes nonessential animation
- No decoded frames, tensors, or buffers enter React state
- Cancellation remains responsive during analysis
- No protected media, filenames, URLs, thumbnails, frame pixels, or class probabilities are committed

Run the checks required by `AGENTS.md` for implementation changes. For docs-only changes, run `pnpm format:check`.

## Reference guidance

This page reflects patterns from production design systems, but repository architecture and status remain authoritative.

- [GOV.UK Design System file upload](https://design-system.service.gov.uk/components/file-upload/)
- [GOV.UK Design System error message](https://design-system.service.gov.uk/components/error-message/)
- [Carbon Design System file uploader](https://preview.carbondesignsystem.com/building-blocks/core/components/file-uploader/guidelines)
- [Apple Human Interface Guidelines file management](https://developer.apple.com/design/human-interface-guidelines/file-management)
- [Web Content Accessibility Guidelines 2.2 updates](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
