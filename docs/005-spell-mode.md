# Sign Spaces (generalized "grouping"/spell-mode) — Design Spec v2

Status: DESIGN, not implemented. Self-contained for a fresh context — this
file replaces the earlier spell-only draft (v1 was spell mode only; v2
generalizes to user-defined spaces). Related: `ARCHITECTURE.md`,
`004-camera-pipeline-vision-models.md`.

---

## 1. Problem

The current pipeline handles only fixed gestures → words. Arbitrary words
(e.g. "EUROPE") must be fingerspelled, and beyond that, users may want
*namespaced vocabularies* (digits, colors, a topic-specific sign set) that
only match while switched on, never colliding with normal keywords.

Generalized flow (Spell Mode is the flagship case):

```
I GOING   [ SPELL_MODE on ]  E U R O P E  [ off ]      →  I, GOING, [EUROPE]
```

While a space is active, scoring matches **that space's signs** (+ control
signs), never the rest of the library.

---

## 2. Chosen architecture — "Sign Spaces" (v2 decision)

### 2.1 What a Sign Space is

A first-class entity the user creates in the admin center:

```json
{
  "id": "spc_e3a1",
  "key": "SPELL_MODE",
  "name": "Spell Mode",
  "join_mode": "spell",             // "spell" | "words"
  "toggle_mode": "shared",          // "shared" | "separate"
  "gesture_ids": ["<id>", "..."],   // member signs (letters, digits, ...)
  "built_in": true
}
```

- `key`: uppercase machine key shown in the UI (`SPELL_MODE`, `NUMBERS`) —
  auto-generated from the name, editable, unique. **Used only for display
  and human greppability; never parsed in code.**
- `gesture_ids`: membership by **gesture id**, not by name prefix. Robust to
  renames; no string matching.
- `join_mode` — chosen at space creation, decides packaging only. Buffer
  processing (outlier filter, dedups, persistence, inactivity close) is
  EXACTLY the same as normal gestures in both modes, because scoping only
  changes what gets scored, not how detection flows:
  - `"spell"` — accepted member signs accumulate into `space_buffer` and the
    whole set closes as ONE word token (`[EUROPE]`). This is fingerspelling.
  - `"words"` (default for new spaces) — every accepted member sign is its
    OWN word token, emitted immediately (`RED`, `BLUE`). The space is just a
    namespaced vocabulary: safety via scope, packaging identical to a normal
    gesture. Nothing accumulates; exit flushes nothing.
- `toggle_mode`:
  - `separate` — the space has an explicit entry sign and (optional) exit
    sign. Implemented as: one gesture stored with role `space-entry`, one
    with role `space-exit` (exit may be omitted → close on inactivity
    timeout only).
  - `shared` — one sign toggles: accepted once → enter, accepted again →
    exit. (Member gesture carries role `space-toggle`.)
- `built_in: true` for the pre-seeded **Spell Mode** space so users don't
  have to create it; it is still editable.

### 2.2 Gesture-side fields (data/gestures.json — single store)

Each gesture gains (one-time backfill on load; default `"normal"`):

```json
{
  "id": "a1f6...",
  "name": "A",
  "display_name": "SPELL_MODE · A",
  "role": "normal",          // "normal" | "space-entry" | "space-exit"
                             // | "space-toggle" | "space-sign"
  "preview_path": "...",
  "landmarks": [...],
  "hand_count": 1,
  "threshold": 72
}
```

- `role` is the runtime source of truth. Membership and scoping are computed
  from ids + roles; **no code path looks for `SPELL_MODE_` in names.**
  Prefixes appear only in `display_name` (e.g. `SPELL_MODE · A`), generated
  by the admin UI for eyeballing.
- A letter "A" sign and a normal keyword sign may use near-identical hand
  shapes — allowed, because scoping happens at scoring time (§3), not
  storage.

### 2.3 Why not name-prefix membership (user's original idea)

- Renames silently break membership.
- Same prefix elsewhere ("open NUMBERS_", typo'd "NUMBERS_MODE" gestures)
  leaks members across groups.
- Every consumer (frontend, decision model, tests) ends up parsing strings.
- id-ref membership keeps `key` pure display and works when a sign belongs
  to multiple spaces.

---

## 3. Runtime model (pipeline)

New module: `src/spell/spell_tracker.py` (rename to `src/spaces/space_tracker.py`
when implementing).

State:

```
active_space: Optional[space_id] = None   # None = standard space
```

Transitions fire on `accepted` events whose gesture role is a control role:

| when in standard | accepted entry sign | → active_space = its space |
| when in space X  | accepted X's exit sign or toggle again | → None (standard) |
| any mode         | other spaces' control signs | ignored (not in scope) |

Scoping — `RealTimePipeline.process_frame` filters the candidate list
**before** `score_gestures`:

- standard: roles `normal` + all space-entry + all space-toggle (+ exits if
  registered separately; choose in admin)
- space X: X's member gestures (role `space-sign`) + X's exit/toggle only

`buffer_state` gains:

```
"active_space": "spc_e3a1" | null,
"space_buffer": ["E", "U", ...]      // live, only while active
```

Word/token output (tokens carry `"mode"` so the frontend never has to look
up the space to render):

```
spell mode, closed by exit/toggle/inactivity:
  {"type": "space", "space": "SPELL_MODE", "mode": "spell", "letters": ["E","U","R","O","P","E"]}
words mode, emitted per acceptance:
  {"type": "space", "space": "COLORS", "mode": "words", "letters": ["RED"]}
```

- Multiple spaces may be open in sequence; only one active at a time (no
  nesting for now — listed in non-goals).
- Inactivity timeout already exists (`end_signal_frames`); reaching it while
  a space is open implicitly closes it and flushes the token.
- `GestureBuffer` stays unaware of spaces; `RealTimePipeline` owns the
  tracker and routes token events. Letter/event details carry `role` so
  downstream can route tokens.

---

## 4. Admin center UI (registration page)

One new control, driven by the same registration screen:

```
Sign type:   ( ) Standard    ( ) Space member    ( ) Space control
```

- **Space member**: shows a space picker (existing spaces + "New space…").
  For Spell Mode the picker becomes a letter/digit select (A–Z, 0–9);
  name field fills automatically ("A"…). Other user spaces use free text.
- **Space control**: sub-choice entry / exit / toggle + space picker.
- Spaces management panel (can be a tab inside admin center):

  - list spaces with member count, preview chips
  - create / rename (regenerates `key`)/ delete (members fall back to
    `normal` with a confirm)
  - per space: pick entry gesture, exit gesture, or mark a gesture as toggle
  - pre-seeded row: "Spell Mode (built-in)" editable like any other

- Gesture list: filter chip per space + thin role badge on rows.

---

## 5. Frontend (playground) impact

- Card 3: while a space is active, the detecting row's label becomes that
  space's key ("SPELL_MODE · Detecting") and accumulated glyphs show live.
- Card 4 queue: space tokens render as bracketed word chips —
  `[EUROPE]` (one chip), instead of per-letter tiles; plain gestures keep
  existing tile rendering.
- `classifyFrame` (pg-flog.js) unchanged — events carry names already.
- The settings heart modal / header controls are untouched.

---

## 6. Implementation phases

1. **Store+backend (DONE, 2026-10-26)**: gestures.json `role` backfill;
   `data/sign_spaces.json` seed + CRUD; `src/spaces/space_tracker.py` scope
   filtering + toggle/entry/exit/inactivity transitions + spell/words tokens;
   `/api/spaces` REST; `/api/gestures/save` accepts role+space_id; 49-case
   synthetic test green (incl. identical-feature cross-space leak check).
2. **P2 — admin UI**: sign-type selector, space picker, spaces panel CRUD
   (name/key, toggle_mode, join_mode), role badges/filter chips.
3. **P3 (pipeline) — DONE** (see 1).
4. **P4 — playground cards 3/4 rendering + end-to-end test script.**

Phases 3/4 land before the sentence decision model (card 5) and speech
output — those consume the tokens.

---

## 7. Acceptance criteria

1. Old `data/gestures.json` (no `role`s, no spaces) loads + behaves exactly
   as today.
2. Registering "A" as a Spell Mode member never affects standard-mode
   scoring of any existing gesture.
3. Entry/exit/toggle flows all close a space; every path flushes a
   `{"type": "space", ...}` token; inactivity auto-close works.
4. Two spaces using overlapping hand shapes never leak members while the
   other is active.
5. Deleting a space returns its gestures to `normal` without data loss.
6. No non-test code path searches gesture **names** for any space key.

---

## 8. Non-goals (deferred)

- Sentence model / NLP joining (card 5) — later.
- Nested spaces (space inside a space).
- Per-letter timing models or per-space thresholds (global threshold stands;
  revisit if letters mis-detect).
- Voice/speech output — separate card.
