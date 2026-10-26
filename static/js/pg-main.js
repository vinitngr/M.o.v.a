/* ------------------------------------------------------------
   5. Main — camera + device picker, header controls, settings
      modal, frame streaming through /ws/pipeline
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
  $('pgStopBtn').classList.add('is-running');
  $('pgStopLabel').textContent = 'Stop';
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
  $('pgStopBtn').classList.remove('is-running');
  $('pgStopLabel').textContent = 'Start';
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
  toggleCamera();
};

function toggleCamera() {
  if (running) {
    stop();
    camMenu.hidden = true;
    return;
  }
  startCamera().catch(err => {
    stop();
    alert(`Could not open camera: ${err.message}`);
  });
}

// Header controls
$('pgStopBtn').onclick = toggleCamera;

function sendControl(payload) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload));
}

$('pgResetBtn').onclick = () => {
  // Pushes a buffer reset to the pipeline (card 3 flips back to empty via
  // the ack message) but never touches camera or streaming state.
  sendControl({ action: 'reset' });
  clearFrameLog();
  clearBufferCard();
  clearQueueCard();
};

/* ------------------------------------------------------------
   4c. Processing settings (heart button → modal)
   ------------------------------------------------------------ */
const pgSettings = { fps: TARGET_FPS, threshold: 65, timeoutFrames: 14 };
const settingsModal = $('pgSettingsModal');

function applyFpsSetting(v) {
  pgSettings.fps = v;
  TARGET_FPS = v;
  FRAME_INTERVAL = Math.round(1000 / v);
  $('pgSetFpsVal').textContent = `${v} fps`;
}

function applyTimeoutSetting(v) {
  pgSettings.timeoutFrames = v;
  $('pgSetTimeoutVal').textContent = `${v} fr ≈ ${(v / TARGET_FPS).toFixed(1)}s`;
  sendControl({ action: 'set_timeout', frames: v });
}

function applyThresholdSetting(v) {
  pgSettings.threshold = v;
  $('pgSetThreshVal').textContent = `${v}%`;
  sendControl({ action: 'set_threshold', threshold: v });
}

$('pgHeartBtn').onclick = () => { settingsModal.hidden = false; };
$('pgSettingsClose').onclick = () => { settingsModal.hidden = true; };
settingsModal.querySelector('.pg-settings-backdrop').onclick = () => { settingsModal.hidden = true; };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') settingsModal.hidden = true;
});

$('pgSetFps').oninput = e => applyFpsSetting(+e.target.value);
$('pgSetTimeout').oninput = e => applyTimeoutSetting(+e.target.value);
$('pgSetThresh').oninput = e => applyThresholdSetting(+e.target.value);

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
        // Apply the playground tuning (heart-button settings) to this
        // pipeline instance — admin's live pipeline stays untouched.
        socket.send(JSON.stringify({
          action: 'init',
          threshold: pgSettings.threshold,
          frames: pgSettings.timeoutFrames,
        }));
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
