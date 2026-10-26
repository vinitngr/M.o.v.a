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
      overlayCtx.fillStyle = FINGERTIPS.includes(idx) ? '#ff5938' : '#5fd8ff';
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
      ctx.fillStyle = FINGERTIPS.includes(i) ? '#ff5938' : 'rgba(95, 216, 255, 0.95)';
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
