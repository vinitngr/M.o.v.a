/* ------------------------------------------------------------
   4b. Card 4 · Gesture Queue (sequences handed over by card 3)
   ------------------------------------------------------------ */
const queueList = $('pgQueueList');
const pgQueue = []; // { parts: [...] } — newest first; see buildQueueParts
let queuePrevStatus = 'idle';

function tokenPart(t) {
  return { kind: 'token', token: t };
}

function buildQueueParts(names, tokens) {
  // Control / member names never reach the queue directly: group content
  // arrives packaged as space tokens. Each token carries `pos`, the raw
  // sequence index where it was flushed — tokens are interleaved there so
  // the queued sentence keeps its true order (spell word before/after
  // adjacent normal gestures).
  const sorted = (tokens || []).slice().sort((a, b) => (a.pos || 0) - (b.pos || 0));
  const parts = [];
  let ti = 0;
  names.forEach((name, idx) => {
    while (ti < sorted.length && (sorted[ti].pos || 0) <= idx) {
      parts.push(tokenPart(sorted[ti]));
      ti += 1;
    }
    const role = roleByGestureName.get(name) || 'normal';
    if (role !== 'normal') return;
    parts.push({ kind: 'name', name });
  });
  while (ti < sorted.length) {
    parts.push(tokenPart(sorted[ti]));
    ti += 1;
  }
  return parts;
}

function tokenLabel(t) {
  const letters = t.letters || [];
  return t.mode === 'spell' ? letters.join('') : letters[0] || '';
}

function buildTokenChip(t) {
  const chip = document.createElement('span');
  chip.className = 'pg-queue-token';
  const key = document.createElement('i');
  key.textContent = t.space;
  const word = document.createElement('b');
  word.textContent = tokenLabel(t);
  chip.append(key, word);
  return chip;
}

function buildPart(part) {
  if (part.kind === 'token') return buildTokenChip(part.token);
  const tile = document.createElement('span');
  tile.className = 'pg-queue-tile';
  const canvas = document.createElement('canvas');
  canvas.width = 84;
  canvas.height = 84;
  tile.append(canvas);
  const g = libraryByName.get(part.name);
  drawThumbSkeleton(canvas, g ? g.landmarks : null);
  return tile;
}

function renderQueueBoard() {
  $('pgQueueCount').textContent = pgQueue.length;

  const rows = [];
  pgQueue.forEach((item, i) => {
    const row = document.createElement('li');
    row.className = 'pg-queue-row';

    const num = document.createElement('span');
    num.className = 'pg-queue-num';
    num.textContent = String(i + 1);

    const thumbs = document.createElement('span');
    thumbs.className = 'pg-queue-thumbs';
    const shown = item.parts.slice(0, 8);
    shown.forEach(part => thumbs.append(buildPart(part)));
    if (item.parts.length > shown.length) {
      const more = document.createElement('span');
      more.className = 'pg-buffer-plus';
      more.textContent = `+${item.parts.length - shown.length}`;
      thumbs.append(more);
    }

    const arrow = document.createElement('span');
    arrow.className = 'pg-queue-arrow';
    arrow.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16m-6-6 6 6-6 6"/></svg>';

    const status = document.createElement('span');
    status.className = 'pg-queue-dot is-queued';
    status.title = 'Queued';

    row.append(num, thumbs, arrow, status);
    rows.push(row);
  });

  if (!rows.length) {
    const empty = document.createElement('li');
    empty.className = 'pg-queue-empty';
    const plus = document.createElement('span');
    plus.className = 'pg-buffer-plus';
    plus.textContent = '+';
    empty.append(plus, 'Complete a gesture sequence → it lands here');
    rows.push(empty);
  }

  queueList.replaceChildren(...rows);
}

function clearQueueCard() {
  pgQueue.length = 0;
  queuePrevStatus = 'idle';
  renderQueueBoard();
}

function renderQueueStatus(data) {
  const bState = data.buffer_state || {};
  const status = bState.status || 'idle';

  // collecting → completed = the buffer just sent a sequence to the queue.
  // All group tokens of this span live in buffer_state.sequence_tokens
  // alongside the raw names — one frame carries the whole sentence.
  if (status === 'completed' && queuePrevStatus === 'collecting') {
    const parts = buildQueueParts(bState.completed_sequence || [], bState.sequence_tokens || []);
    if (parts.length) {
      pgQueue.unshift({ parts });
      renderQueueBoard();
    }
  }
  queuePrevStatus = status;
}

pipelineListeners.push(renderQueueStatus);
