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

function clearBufferCard() {
  liveName = null;
  liveStreak = 0;
  prevBufferStatus = 'idle';
  renderedBufferKey = '';
  liveRowRefs = null;
}
