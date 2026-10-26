/* ------------------------------------------------------------
   4b. Card 4 · Gesture Queue (sequences handed over by card 3)
   ------------------------------------------------------------ */
const queueList = $('pgQueueList');
const pgQueue = []; // { seq: [gesture name, ...] } — newest first
let queuePrevStatus = 'idle';

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
    const shown = item.seq.slice(0, 6);
    shown.forEach(name => {
      const tile = document.createElement('span');
      tile.className = 'pg-queue-tile';
      const canvas = document.createElement('canvas');
      canvas.width = 84;
      canvas.height = 84;
      tile.append(canvas);
      const g = libraryByName.get(name);
      drawThumbSkeleton(canvas, g ? g.landmarks : null);
      thumbs.append(tile);
    });
    if (item.seq.length > shown.length) {
      const more = document.createElement('span');
      more.className = 'pg-buffer-plus';
      more.textContent = `+${item.seq.length - shown.length}`;
      thumbs.append(more);
    }

    const arrow = document.createElement('span');
    arrow.className = 'pg-queue-arrow';
    arrow.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16m-6-6 6 6-6 6"/></svg>';

    const status = document.createElement('span');
    status.className = 'pg-queue-status';
    status.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3.5 2"/></svg>Queued';

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

  // collecting → completed = the buffer just sent a sequence to the queue
  if (status === 'completed' && queuePrevStatus === 'collecting') {
    const seq = bState.completed_sequence || [];
    if (seq.length) {
      pgQueue.unshift({ seq: [...seq] });
      renderQueueBoard();
    }
  }
  queuePrevStatus = status;
}

pipelineListeners.push(renderQueueStatus);
