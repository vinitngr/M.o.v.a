/* ============================================================
   MOVA Playground — shared infra and utilities
   Loaded first: DOM helpers, pipelineListeners dispatch, camera
  /socket state, gesture library cache, skeleton drawing.
   Per-card modules (pg-card1 / pg-flog / pg-buffer / pg-queue)
   register a listener in `pipelineListeners`; pg-main wires
   camera, header controls and the settings modal.
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
        if (pgQueue.length) renderQueueBoard();
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
