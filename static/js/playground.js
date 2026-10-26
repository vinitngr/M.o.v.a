/* ============================================================
   MOVA Playground — page logic
   Structure:
     1. Shared infra (ws frame streaming, camera, library cache)
     2. Card 1 · Live Gesture Input  (overlay + top-5)
     3. Card 2 · Frame Analysis      (per-frame processing log)
   Cards 3–5 later: register a listener in `pipelineListeners`.
   ============================================================ */

const $ = id => document.getElementById(id);

const HAND_LINKS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17]
];
const FINGERTIPS = [4, 8, 12, 16, 20];

/* ------------------------------------------------------------
   1. Shared infra
   ------------------------------------------------------------ */
let stream = null;
let socket = null;
let running = false;
let sending = false;
let lastSendAt = 0;
let fpsHistory = [];
let TARGET_FPS = 6;
let FRAME_INTERVAL = Math.round(1000 / TARGET_FPS);

let libraryById = null;   // id -> {name, landmarks, preview_path}
let libraryPromise = null;

const video = $('pgVideo');
const stage = $('pgStage');
const overlay = $('pgOverlay');
const overlayCtx = overlay.getContext('2d');
const grabCanvas = document.createElement('canvas');
const grabCtx = grabCanvas.getContext('2d');

// Card modules hook in here — each new card appends its handler
const pipelineListeners = [];

function dispatchPipelineData(data) {
  for (const fn of pipelineListeners) {
    try {
      fn(data);
    } catch (err) {
      console.error('Playground card render failed:', err);
    }
  }
}

let libraryByName = new Map();

function ensureLibrary() {
  if (!libraryPromise) {
    libraryPromise = fetch('/api/playground/library')
      .then(r => r.json())
      .then(data => {
        libraryById = new Map();
        libraryByName = new Map();
        for (const g of (data.gestures || [])) {
          libraryById.set(g.id, g);
          libraryByName.set(g.name, g);
        }
        // Cached buffer rows may lack thumbnails — force one rebuild
        renderedBufferKey = '';
        return libraryById;
      })
      .catch(() => {
        libraryById = new Map();
        libraryByName = new Map();
        return libraryById;
      });
  }
  return libraryPromise;
}

function getVideoCoverRect(vid, boxW, boxH) {
  if (!vid.videoWidth || !vid.videoHeight) {
    return { x: 0, y: 0, w: boxW, h: boxH };
  }
  const va = vid.videoWidth / vid.videoHeight;
  const ba = boxW / boxH;
  let w, h;
  if (ba > va) {
    w = boxW;
    h = w / va;
  } else {
    h = boxH;
    w = h * va;
  }
  return { x: (boxW - w) / 2, y: (boxH - h) / 2, w, h };
}

function nowTime() {
  return new Date().toLocaleTimeString('en-GB', { hour12: false });
}

/* ------------------------------------------------------------
   2. Card 1 · Live Gesture Input
   ------------------------------------------------------------ */
function drawOverlay(hands) {
  const rect = overlay.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  overlay.width = Math.max(1, rect.width * scale);
  overlay.height = Math.max(1, rect.height * scale);
  overlayCtx.setTransform(scale, 0, 0, scale, 0, 0);
  overlayCtx.clearRect(0, 0, rect.width, rect.height);

  if (!hands || !hands.length || !video.videoWidth) return;

  const vRect = getVideoCoverRect(video, rect.width, rect.height);
  const point = p => [vRect.x + p[0] * vRect.w, vRect.y + p[1] * vRect.h];

  overlayCtx.lineWidth = 2;
  overlayCtx.strokeStyle = '#38bdf8';

  for (const hand of hands) {
    overlayCtx.beginPath();
    for (const [a, b] of HAND_LINKS) {
      const s = point(hand[a]);
      const e = point(hand[b]);
      overlayCtx.moveTo(s[0], s[1]);
      overlayCtx.lineTo(e[0], e[1]);
    }
    overlayCtx.stroke();

    hand.forEach((p, idx) => {
      const [x, y] = point(p);
      overlayCtx.beginPath();
      overlayCtx.arc(x, y, FINGERTIPS.includes(idx) ? 3.6 : 3, 0, Math.PI * 2);
      overlayCtx.fillStyle = FINGERTIPS.includes(idx) ? '#00e6a8' : '#5fd8ff';
      overlayCtx.fill();
    });
  }
}

function createRow() {
  const li = document.createElement('li');
  li.className = 'pg-row is-empty';

  const thumb = document.createElement('div');
  thumb.className = 'pg-thumb';
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const img = document.createElement('img');
  img.alt = '';
  img.hidden = true;
  thumb.append(canvas, img);

  const name = document.createElement('span');
  name.className = 'pg-row-name';
  name.textContent = '—';

  const bar = document.createElement('span');
  bar.className = 'pg-row-bar';
  const fill = document.createElement('span');
  fill.className = 'pg-row-fill';
  bar.append(fill);

  const score = document.createElement('span');
  score.className = 'pg-row-score';
  score.textContent = '';

  li.append(thumb, name, bar, score);
  return li;
}

// points may be [x,y] or [x,y,z]; single hand (21) or two hands (42, left+right)
function buildThumbPoints(g) {
  const pts = g && g.landmarks;
  if (!Array.isArray(pts) || !pts.length || !Array.isArray(pts[0])) return null;
  return pts.map(p => [Number(p[0]), Number(p[1])]);
}

function drawThumbSkeleton(canvas, points) {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!points || !points.length) return false;
  // Accepts flat [21/42 pts] (library) AND nested [[hand pts], ...] (live frames)
  if (Array.isArray(points[0][0])) points = points.flat();
  if (!points.length || !Number.isFinite(points[0][0])) return false;
  const hands = points.length > 21
    ? [points.slice(0, 21), points.slice(21, 42)]
    : [points];
  const flats = hands.map(hand => hand.map(p => [Number(p[0]) || 0, Number(p[1]) || 0]));

  // Shared bbox keeps both hands in their true relative placement
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const flat of flats) {
    for (const [x, y] of flat) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
  }
  const bw = Math.max(maxX - minX, 0.02);
  const bh = Math.max(maxY - minY, 0.02);

  const W = canvas.width, H = canvas.height, pad = 10;
  const s = Math.min((W - pad * 2) / bw, (H - pad * 2) / bh);
  const ox = (W - bw * s) / 2;
  const oy = (H - bh * s) / 2;
  const pt = (flat, i) => [ox + (flat[i][0] - minX) * s, oy + (flat[i][1] - minY) * s];

  for (const flat of flats) {
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.9)';
    ctx.beginPath();
    for (const [a, b] of HAND_LINKS) {
      const p1 = pt(flat, a), p2 = pt(flat, b);
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
    }
    ctx.stroke();

    flat.forEach((p, i) => {
      const [x, y] = pt(flat, i);
      ctx.beginPath();
      ctx.arc(x, y, FINGERTIPS.includes(i) ? 2.6 : 2.1, 0, Math.PI * 2);
      ctx.fillStyle = FINGERTIPS.includes(i) ? '#00e6a8' : 'rgba(95, 216, 255, 0.95)';
      ctx.fill();
    });
  }
  return true;
}

let renderedOrderKey = '';
const rows = [];
(function initTop5() {
  const top5 = $('pgTop5');
  for (let i = 0; i < 5; i++) {
    const row = createRow();
    top5.append(row);
    rows.push({
      el: row,
      canvas: row.querySelector('canvas'),
      img: row.querySelector('img'),
      name: row.querySelector('.pg-row-name'),
      fill: row.querySelector('.pg-row-fill'),
      score: row.querySelector('.pg-row-score'),
      gestureId: null,
    });
  }
})();

function renderRowThumb(row) {
  const g = row.gestureId && libraryById ? libraryById.get(row.gestureId) : null;
  const pts = buildThumbPoints(g);
  if (pts && drawThumbSkeleton(row.canvas, pts)) {
    row.canvas.hidden = false;
    row.img.hidden = true;
  } else if (g && g.preview_path) {
    row.img.src = g.preview_path;
    row.img.hidden = false;
    row.canvas.hidden = true;
  } else {
    row.canvas.hidden = false;
    row.img.hidden = true;
    row.canvas.getContext('2d').clearRect(0, 0, row.canvas.width, row.canvas.height);
  }
}

function renderTop5(scores) {
  ensureLibrary();

  const list = (scores || []).slice(0, 5);
  const orderKey = list.map(s => s.id).join('|');
  const orderChanged = orderKey !== renderedOrderKey;

  list.forEach((s, i) => {
    const row = rows[i];
    if (row.gestureId !== s.id) {
      row.gestureId = s.id;
      row.name.textContent = s.name;
      renderRowThumb(row);
    }
    row.el.classList.remove('is-empty');
    row.el.classList.toggle('is-active', i === 0);
    row.fill.style.width = `${Math.max(0, Math.min(100, s.score))}%`;
    row.score.textContent = (s.score / 100).toFixed(2);
  });

  for (let i = list.length; i < 5; i++) {
    const row = rows[i];
    if (row.gestureId !== null || orderChanged) {
      row.gestureId = null;
      row.name.textContent = '—';
      renderRowThumb(row);
    }
    row.fill.style.width = '0%';
    row.score.textContent = '';
  }

  renderedOrderKey = orderKey;
}

function recordFps() {
  const now = performance.now();
  fpsHistory.push(now);
  if (fpsHistory.length > 8) fpsHistory.shift();
  if (fpsHistory.length >= 2) {
    const dur = (now - fpsHistory[0]) / 1000;
    if (dur > 0) {
      $('pgFpsBadge').textContent = `${((fpsHistory.length - 1) / dur).toFixed(1)} FPS`;
    }
  }
}

function setHandPill(count) {
  const pill = $('pgHandPill');
  pill.textContent = count ? `${count} hand${count === 1 ? '' : 's'}` : 'no hands';
  pill.classList.toggle('is-hands', !!count);
}

pipelineListeners.push(data => {
  setHandPill(data.hand_count || 0);
  renderTop5(data.scores || []);
  drawOverlay(data.landmarks || []);
});

/* ------------------------------------------------------------
   3. Card 2 · Frame Analysis (what got selected / filtered)
   ------------------------------------------------------------ */
const FRAME_LOG_MAX = 36;
const frameLogOl = $('pgFrameLog');
let frameSerial = 0;

const chipLabels = {
  selected: 'Selected',
  duplicate: 'Duplicate',
  rejected: 'Rejected',
  outlier: 'Outlier',
  completed: 'Completed',
};

const counters = {};
for (const key of Object.keys(chipLabels)) {
  counters[key] = 0;
}

function chipColorClass(eventType) {
  if (eventType === 'accepted') return 'selected';
  if (eventType === 'duplicate') return 'duplicate';
  if (eventType === 'outlier') return 'outlier';
  if (eventType === 'completed') return 'completed';
  return 'rejected';
}

// Decision table for one processed frame (mirrors what the buffer did):
//  buffer event (accepted | duplicate | outlier | completed) → authoritative
//  no event + no hands           → Rejected / No hand detected
//  no event + best match         → Duplicate (dedup / persistence filter)
//  no event + hand, below thresh → Rejected / <top candidate name>
function classifyFrame(data) {
  const ev = data.latest_event;
  const bState = data.buffer_state || {};
  const hands = data.hand_count || 0;
  const top = (data.scores || [])[0] || null;

  if (ev) {
    if (ev.event_type === 'accepted') {
      return { status: 'selected', name: ev.gesture };
    }
    if (ev.event_type === 'duplicate') {
      return { status: 'duplicate', name: ev.gesture };
    }
    if (ev.event_type === 'outlier') {
      const conf = ev.details?.confidence;
      const confTxt = Number.isFinite(conf) ? ` (${(conf / 100).toFixed(2)})` : '';
      return {
        status: 'outlier',
        name: `${ev.gesture}${confTxt}`,
        note: 'Unexpected gesture',
        title: ev.details?.reason || ev.message,
      };
    }
    if (ev.event_type === 'completed') {
      return {
        status: 'completed',
        name: 'Sequence ended',
        note: (ev.details?.sequence || []).join(' + '),
      };
    }
  }

  if (!hands) {
    return { status: 'rejected', name: 'No hand detected' };
  }
  if (data.best_match) {
    // Recognized above threshold, but buffer took no action (dedup / warm-up)
    return { status: 'duplicate', name: data.best_match.name };
  }
  return { status: 'rejected', name: top ? top.name : 'Unknown pose' };
}

// Only these statuses collapse into "+N" runs; selected / outlier /
// completed stay as individual rows (they're rare and worth seeing).
const MERGEABLE_STATUSES = { rejected: true, duplicate: true };

function buildLogEntry(time, serial, landmarks, info) {
  const li = document.createElement('li');
  li.className = 'pg-log';
  li.title = info.title || '';
  if (MERGEABLE_STATUSES[info.status]) {
    li.classList.add('pg-log-run');
    li.dataset.status = info.status;
    li.dataset.name = info.name ?? '';
  }

  const thumb = document.createElement('span');
  thumb.className = 'pg-log-thumb';
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  if (!(landmarks || []).length || !drawThumbSkeleton(canvas, landmarks)) {
    // no hand in frame — faint dashed circle placeholder
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = 'rgba(117, 133, 146, 0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(canvas.width / 2, canvas.height / 2, 7, 0, Math.PI * 2);
    ctx.stroke();
  }
  thumb.append(canvas);

  const main = document.createElement('span');
  main.className = 'pg-log-main';
  const topLine = document.createElement('span');
  topLine.className = 'pg-log-top';
  const timeSpan = document.createElement('span');
  timeSpan.className = 'pg-log-time';
  timeSpan.textContent = time;
  const numLine = document.createElement('span');
  numLine.className = 'pg-log-num';
  numLine.textContent = `#${serial}`;
  topLine.append(timeSpan, numLine);
  const nameLine = document.createElement('span');
  nameLine.className = 'pg-log-gesture';
  nameLine.textContent = info.name || '—';
  main.append(topLine, nameLine);

  const side = document.createElement('span');
  side.className = 'pg-log-side';
  const chipRow = document.createElement('span');
  chipRow.className = 'pg-log-chip-row';
  const chip = document.createElement('span');
  chip.className = `pg-log-chip is-${info.status}`;
  chip.textContent = chipLabels[info.status];
  chipRow.append(chip);
  if (MERGEABLE_STATUSES[info.status]) {
    const runCount = document.createElement('span');
    runCount.className = 'pg-log-run-count';
    runCount.hidden = true;
    chipRow.append(runCount);
  }
  side.append(chipRow);
  if (info.note) {
    const note = document.createElement('span');
    note.className = 'pg-log-note';
    note.textContent = info.note;
    side.append(note);
  }

  li.append(thumb, main, side);
  return li;
}

function pushEmptyLogNote() {
  if (frameLogOl.children.length) return;
  const li = document.createElement('li');
  li.className = 'pg-log-empty';
  li.textContent = 'Start the camera — every processed frame lands here.';
  frameLogOl.append(li);
}

function renderFrameLog(data) {
  frameSerial += 1;
  // Skip silent no-hand frames — only log them if the buffer emitted an
  // event (e.g. a completed sequence), otherwise they're pure noise.
  const hasHands = (data.landmarks || []).length > 0;
  if (!hasHands && !data.latest_event) return;
  const info = classifyFrame(data);
  counters[info.status] = (counters[info.status] || 0) + 1;

  $('pgCntSel').textContent = counters.selected;
  $('pgCntDup').textContent = counters.duplicate;
  $('pgCntRej').textContent = counters.rejected;
  $('pgCntOut').textContent = counters.outlier;

  const emptyNote = frameLogOl.querySelector('.pg-log-empty');
  if (emptyNote) emptyNote.remove();

  // Collapse consecutive rejected/duplicate frames into one row:
  // skeleton + name stay from the run's first frame (least recent),
  // time + frame number tick with the newest, counter grows (+N).
  const time = nowTime();
  const topRow = frameLogOl.firstElementChild;
  if (
    MERGEABLE_STATUSES[info.status] &&
    topRow?.classList.contains('pg-log-run') &&
    topRow.dataset.status === info.status &&
    topRow.dataset.name === (info.name ?? '')
  ) {
    const extras = (parseInt(topRow.dataset.extras || '0', 10) + 1);
    topRow.dataset.extras = String(extras);
    topRow.querySelector('.pg-log-run-count').textContent = `+${extras}`;
    topRow.querySelector('.pg-log-run-count').hidden = false;
    topRow.querySelector('.pg-log-time').textContent = time;
    topRow.querySelector('.pg-log-num').textContent = `#${frameSerial}`;
    return;
  }

  const entry = buildLogEntry(time, frameSerial, data.landmarks, info);
  frameLogOl.prepend(entry);

  while (frameLogOl.children.length > FRAME_LOG_MAX) {
    frameLogOl.lastChild.remove();
  }
}

pipelineListeners.push(renderFrameLog);

function clearFrameLog() {
  frameSerial = 0;
  for (const key of Object.keys(counters)) counters[key] = 0;
  $('pgCntSel').textContent = '0';
  $('pgCntDup').textContent = '0';
  $('pgCntRej').textContent = '0';
  $('pgCntOut').textContent = '0';
  frameLogOl.replaceChildren();
  pushEmptyLogNote();
}

/* ------------------------------------------------------------
   4. Card 3 · Active Gesture Buffer (stable rows + live row,
      inactivity timeout bar that hands the sequence to card 4)
   ------------------------------------------------------------ */
const SVG_NS = 'http://www.w3.org/2000/svg';
const RING_CIRC = 2 * Math.PI * 12.5;
const bufList = $('pgBufferList');
let prevBufferStatus = 'idle';
let liveName = null;
let liveStreak = 0;
let queuedHintTimer = null;
// Re-creating rows at ~6 FPS re-triggered their entrance animation (flicker).
// Rows are only rebuilt when the sequence contents actually change; the live
// row's ring/skeleton are muted in place every frame.
let renderedBufferKey = '';
let liveRowRefs = null; // { tile, ring:{prog,circ} } for the current Detecting row

function createRing() {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 30 30');
  svg.classList.add('pg-ring');
  const r = 12.5;
  const circ = 2 * Math.PI * r;
  const track = document.createElementNS(SVG_NS, 'circle');
  track.setAttribute('cx', '15'); track.setAttribute('cy', '15');
  track.setAttribute('r', String(r));
  track.classList.add('pg-ring-track');
  const prog = document.createElementNS(SVG_NS, 'circle');
  prog.setAttribute('cx', '15'); prog.setAttribute('cy', '15');
  prog.setAttribute('r', String(r));
  prog.classList.add('pg-ring-fill');
  prog.style.strokeDasharray = `${circ}`;
  prog.style.strokeDashoffset = `${circ}`;
  svg.append(track, prog);
  return { svg, prog, circ };
}

function buildSkeletonTile() {
  const el = document.createElement('span');
  el.className = 'pg-log-thumb';
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  el.append(canvas);
  return { el, canvas, draw: pts => {
    if (pts && drawThumbSkeleton(canvas, pts)) return true;
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = 'rgba(117, 133, 146, 0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(canvas.width / 2, canvas.height / 2, 7, 0, Math.PI * 2);
    ctx.stroke();
    return false;
  } };
}

function buildBufferRow({ index, name, stable, ringProgress, thumbPts }) {
  const li = document.createElement('li');
  li.className = `pg-br-row ${stable ? 'is-stable' : 'is-detecting'}`;

  const tile = buildSkeletonTile();
  li.append(tile.el);
  tile.draw(thumbPts);

  const main = document.createElement('span');
  main.className = 'pg-br-main';
  const top = document.createElement('span');
  top.className = 'pg-br-top';
  const idx = document.createElement('b');
  idx.textContent = `#${index}`;
  top.append(idx, document.createTextNode(' '), Object.assign(document.createElement('span'), { textContent: name, className: 'pg-br-name' }));
  const pill = document.createElement('span');
  pill.className = 'pg-br-pill';
  const dot = document.createElement('i');
  pill.append(dot, stable ? 'Stable' : 'Detecting…');
  main.append(top, pill);
  li.append(main);

  const ring = createRing();
  ring.prog.style.strokeDashoffset = `${ring.circ * (1 - Math.max(0, Math.min(1, ringProgress)))}`;
  li.append(ring.svg);

  return li;
}

function flashQueuedHint() {
  const hint = $('pgQueuedHint');
  hint.classList.add('is-on');
  clearTimeout(queuedHintTimer);
  queuedHintTimer = setTimeout(() => hint.classList.remove('is-on'), 2600);
}

function renderBuffer(data) {
  const bState = data.buffer_state || {};
  const seq = bState.accepted_sequence || [];
  const best = data.best_match;
  const stable = !!best && bState.last_accepted_gesture === best.name;

  // Live streak drives the "Detecting…" ring before the buffer accepts
  if (best && best.name === liveName) liveStreak += 1;
  else { liveName = best ? best.name : null; liveStreak = 1; }

  // Sequence completed → hand-off note into the (future) card 4 queue
  if ((bState.status || 'idle') === 'completed' && prevBufferStatus === 'collecting') {
    flashQueuedHint();
  }
  prevBufferStatus = bState.status || 'idle';

  const hasLiveRow = !!best && !stable;
  const bufferKey = `${seq.join('|')}#${hasLiveRow ? `L:${best.name}` : 'none'}`;

  // Rebuild only when contents change; otherwise just mute in place
  if (bufferKey !== renderedBufferKey) {
    renderedBufferKey = bufferKey;
    bufList.replaceChildren();
    liveRowRefs = null;

    seq.forEach((name, i) => {
      const g = libraryByName.get(name);
      bufList.append(buildBufferRow({
        index: i + 1,
        name,
        stable: true,
        ringProgress: 1,
        thumbPts: g ? g.landmarks : null,
      }));
    });

    if (hasLiveRow) {
      const row = buildBufferRow({
        index: seq.length + 1,
        name: best.name,
        stable: false,
        ringProgress: 0,
        thumbPts: data.landmarks || [],
      });
      // Keep refs to the row's own nodes — per-frame updates mutate them,
      // the DOM structure is never rebuilt (no flicker).
      liveRowRefs = {
        tile: row.querySelector('.pg-log-thumb canvas'),
        ringProg: row.querySelector('.pg-ring-fill'),
      };
      bufList.append(row);
    }

    if (!bufList.children.length) {
      const empty = document.createElement('li');
      empty.className = 'pg-buffer-empty';
      const plus = document.createElement('span');
      plus.className = 'pg-buffer-plus';
      plus.textContent = '+';
      empty.append(plus, 'Waiting for next gesture…');
      bufList.append(empty);
    }

    bufList.scrollTop = bufList.scrollHeight;
  }

  // Per-frame updates without touching the DOM structure (no flicker)
  if (liveRowRefs && hasLiveRow) {
    const p = Math.max(0, Math.min(1, liveStreak / 4));
    liveRowRefs.ringProg.style.strokeDashoffset = `${RING_CIRC * (1 - p)}`;
    liveRowRefs.tile && drawThumbSkeleton(liveRowRefs.tile, data.landmarks || []);
  }

  // Inactivity timeout footer (drives the auto-send to card 4's queue)
  const frames = bState.inactive_frames || 0;
  $('pgInactFill').style.width = `${Math.min(100, bState.inactivity_progress || 0)}%`;
  $('pgInactSec').textContent = `${(frames / TARGET_FPS).toFixed(1)}s`;
}

pipelineListeners.push(renderBuffer);
ensureLibrary();

function clearBufferCard() {
  liveName = null;
  liveStreak = 0;
  prevBufferStatus = 'idle';
  renderedBufferKey = '';
  liveRowRefs = null;
}

/* ------------------------------------------------------------
   4. Camera handling + device picker
   ------------------------------------------------------------ */
async function startCamera(deviceId) {
  if (!navigator.mediaDevices?.getUserMedia) {
    alert('Camera access requires HTTPS or localhost.');
    return;
  }
  const constraints = {
    video: deviceId
      ? { deviceId: { exact: deviceId }, width: { ideal: 960 }, height: { ideal: 720 } }
      : { facingMode: 'user', width: { ideal: 960 }, height: { ideal: 720 } },
    audio: false,
  };
  const media = await navigator.mediaDevices.getUserMedia(constraints);
  stopTracksOnly();
  stream = media;
  video.srcObject = stream;
  await video.play();

  stage.classList.add('is-live');
  const toggle = $('pgCamToggle');
  toggle.classList.remove('is-off');
  $('pgCamLabel').textContent = 'Camera On';
  populateDeviceMenu();

  if (!running) {
    running = true;
    connect();
  }
}

function stopTracksOnly() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
}

function stop() {
  running = false;
  sending = false;
  socket?.close();
  socket = null;
  stopTracksOnly();
  video.srcObject = null;
  camMenu.hidden = true;
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  stage.classList.remove('is-live');
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  const toggle = $('pgCamToggle');
  toggle.classList.add('is-off');
  $('pgCamLabel').textContent = 'Start Camera';
  $('pgFpsBadge').textContent = '0.0 FPS';
  fpsHistory = [];
  setHandPill(0);
  clearFrameLog();
  clearBufferCard();
}

let menuPopulated = false;
async function populateDeviceMenu() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cams = devices.filter(d => d.kind === 'videoinput');
    const menu = $('pgCamMenu');
    const activeId = stream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
    menu.replaceChildren();
    if (!cams.length) {
      const none = document.createElement('button');
      none.className = 'pg-cam-item';
      none.textContent = 'No camera found';
      none.disabled = true;
      menu.append(none);
    }
    cams.forEach((d, i) => {
      const item = document.createElement('button');
      item.className = 'pg-cam-item';
      item.type = 'button';
      item.textContent = d.label || `Camera ${i + 1}`;
      item.classList.toggle('is-active', d.deviceId === activeId);
      item.onclick = () => {
        menu.hidden = true;
        startCamera(d.deviceId).catch(err => alert(`Could not switch camera: ${err.message}`));
      };
      menu.append(item);
    });
    menuPopulated = true;
  } catch {
    menuPopulated = false;
  }
}

const camToggle = $('pgCamToggle');
const camMenu = $('pgCamMenu');

camToggle.onclick = e => {
  if (e.target.closest('#pgCamChev')) {
    if (camMenu.hidden) populateDeviceMenu().then(() => { camMenu.hidden = false; });
    else camMenu.hidden = true;
    return;
  }
  if (running) {
    stop();
    camMenu.hidden = true;
    return;
  }
  startCamera().catch(err => {
    stop();
    alert(`Could not open camera: ${err.message}`);
  });
};

document.addEventListener('click', e => {
  if (!camMenu.hidden && !camToggle.contains(e.target) && !camMenu.contains(e.target)) {
    camMenu.hidden = true;
  }
});

$('pgExpand').onclick = () => {
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  } else {
    stage.requestFullscreen?.().catch(() => {});
  }
};

window.addEventListener('beforeunload', stop);

/* ------------------------------------------------------------
   5. Frame streaming through /ws/pipeline (same as admin)
   ------------------------------------------------------------ */
function sendFrame() {
  if (!running || sending || socket?.readyState !== WebSocket.OPEN || !video.videoWidth) return;

  const va = video.videoWidth / video.videoHeight;
  const w = 480;
  const h = Math.round(480 / va);
  grabCanvas.width = w;
  grabCanvas.height = h;
  grabCtx.drawImage(video, 0, 0, w, h);

  sending = true;
  lastSendAt = performance.now();
  socket.send(JSON.stringify({ image_base64: grabCanvas.toDataURL('image/jpeg', 0.68) }));
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${proto}://${location.host}/ws/pipeline`);

      socket.onopen = () => {
        // Playground default: a slightly friendlier threshold (server default is 72)
        // so gestures you demo get buffered without touching admin's tuning sliders.
        socket.send(JSON.stringify({ action: 'init', threshold: 65 }));
        sendFrame();
      };

  socket.onmessage = event => {
    sending = false;
    recordFps();
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    if (data.error) {
      console.warn('Pipeline error:', data.error);
    } else {
      dispatchPipelineData(data);
    }
    if (running) {
      const wait = Math.max(10, FRAME_INTERVAL - (performance.now() - lastSendAt));
      setTimeout(sendFrame, wait);
    }
  };

  socket.onerror = () => { sending = false; };

  socket.onclose = () => {
    sending = false;
    if (running) setTimeout(connect, 1000);
  };
}

// Preload skeleton thumbnails before the first detection arrives
ensureLibrary();
