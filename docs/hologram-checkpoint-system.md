# Hologram checkpoint system

## Existing architecture

The scene is rendered by a React Three Fiber `Canvas` in `Scene.jsx`. Drei's
`ScrollControls` creates a five-page vertical scroll area, and `CameraRig.jsx`
previously read the damped `scroll.offset` value directly. That normalized
value was mapped linearly from the street entrance at Z `6` to Z `-62`, with a
second damping step applied to the camera position.

`Street.jsx` owns the GLB street and motorcycle, applies runtime materials, and
contains the existing exit-sign interaction. `Rain.jsx` animates a lightweight
line-segment rain field. The canvas already uses a post-processing `Bloom`
pass, so emissive-looking, tone-mapping-independent hologram materials can use
the existing glow without another effect pass. There was no shared journey
progress store and no experimental storefront hologram implementation.

## Implementation

### Files created

- `src/components/holograms/hologramCheckpoints.js` contains checkpoint data.
- `src/components/holograms/HologramSystem.jsx` manages journey progress,
  locking, active/completed state, and scroll synchronization.
- `src/components/holograms/Hologram.jsx` renders and animates a reusable 3D
  panel.

### Files modified

- `src/components/canvas/Scene.jsx` places `HologramSystem` inside the existing
  `ScrollControls` and wraps the street, rain, and camera rig with it.
- `src/components/canvas/CameraRig.jsx` reads the system's effective progress
  ref instead of reading `scroll.offset` directly. Its path and damping remain
  unchanged.

### Checkpoint and scroll behavior

Each frame, `HologramSystem` compares the previous raw progress with the raw
normalized scroll target. If input crosses an available checkpoint in either
direction, it selects the first checkpoint on that path and clamps the scroll
target to its threshold. This catches large wheel deltas, scrollbar jumps,
trackpad momentum, and touch-driven scrolling before they can skip a
checkpoint.

The existing damped progress is allowed to approach the clamped threshold, so
the camera glides to the checkpoint instead of snapping. Once it arrives, the
raw browser scroll target and Drei's damped offset are both kept at the exact
threshold. Input received while the panel is open therefore cannot accumulate
and cause a jump after dismissal.

Clicking or tapping the panel starts its exit animation. When that animation
finishes, its ID is temporarily added to an in-memory `Set`, the lock is
released at the same synchronized progress, and normal scrolling resumes. The
temporary completed state prevents the panel from reopening immediately. Once
the user moves far enough away, the checkpoint is armed again and crossing it
from either direction reopens the hologram. Returning to the street entrance
therefore makes the complete sequence readable again from the beginning.

The exit sign uses the progress context's dedicated return action. During that
smooth trip, checkpoint detection is suspended so the camera goes directly to
the entrance instead of stopping at a hologram. Reaching the entrance clears
the temporary completed state and enables the full sequence again.

### Position and interaction

The panel copies the active camera position and orientation each frame, then
moves six world units down the camera's local forward axis. It therefore stays
centered in the user's visual field and is independent of all street geometry.
Its R3F pointer handlers stop propagation, set a pointer cursor on hover, and
start dismissal on click or tap.

The panel uses transparent cyan and magenta basic materials that work with the
existing Bloom pass. A small camera-local float, scale pulse, scan lines, and a
short scale/opacity transition provide lightweight idle, entrance, and exit
motion. No additional animation or shader dependency was added.

> Holograms are journey checkpoints displayed in front of the user and are not associated with storefronts.

## Configuration

Add another entry to the exported array in
`src/components/holograms/hologramCheckpoints.js`:

```js
{
  id: 'new-hologram',
  triggerProgress: 0.75,
  title: 'NEW HOLOGRAM',
  description: 'OPTIONAL SECONDARY TEXT',
}
```

Keep entries ordered by `triggerProgress`, use unique IDs, and keep progress in
the normalized `0` to `1` range. The visual and checkpoint controller require
no other changes. The initial configuration demonstrates independent behavior
with `TESTNI HOLOGRAM` at `0.25` and `DRUGI TESTNI HOLOGRAM` at `0.60`.

## Testing

- Production Vite build: passed (`699` modules transformed).
- Git whitespace/error check: passed; only line-ending notices from the
  existing Windows checkout were reported.
- Production preview: served successfully on localhost with HTTP `200` for the
  HTML and generated JavaScript asset.
- Bundle inspection: both configured hologram titles are present in the
  generated production asset.
- Browser smoke-test setup was attempted, but the available computer-control
  environment exposed no browser target. Interactive wheel, trackpad, click,
  backward-scroll, and touch checks therefore still require a manual browser
  pass on a machine with a WebGL browser.
- This project defines no separate lint, typecheck, or automated test scripts.

## Future improvements

Possible follow-ups include richer per-checkpoint content, custom panel visuals,
audio cues, advanced glitch shaders, portfolio sections, and more elaborate
transitions. Those features are intentionally outside this implementation.
