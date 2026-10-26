/* ------------------------------------------------------------
   3. Card 2 · Frame Analysis (what got selected / filtered)
   ------------------------------------------------------------ */
const FRAME_LOG_MAX = 36;
const frameLogOl = $('pgFrameLog');
let frameSerial = 0;

const chipLabels = {
  selected: 'Selected',
  duplicate: 'Duplicate',
  pending: 'Predicted',
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
    if (bState.last_accepted_gesture === data.best_match.name) {
      // Recognized again after the buffer already accepted it → dedup
      return { status: 'duplicate', name: data.best_match.name };
    }
    // Above threshold but the buffer hasn't accepted it yet (warm-up /
    // persistence filter) — first sighting, NOT a duplicate
    return { status: 'pending', name: data.best_match.name };
  }
  return { status: 'rejected', name: top ? top.name : 'Unknown pose' };
}

// Only these statuses collapse into "+N" runs; selected / outlier /
// completed stay as individual rows (they're rare and worth seeing).
const MERGEABLE_STATUSES = { rejected: true, duplicate: true, pending: true };

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
  $('pgCntPred').textContent = counters.pending;
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
  $('pgCntPred').textContent = '0';
  $('pgCntRej').textContent = '0';
  $('pgCntOut').textContent = '0';
  frameLogOl.replaceChildren();
  pushEmptyLogNote();
}
