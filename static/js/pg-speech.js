/* ============================================================
   MOVA Playground — card 5: Speech Output
   The LAST stop of the pipeline: a sentence source (one-shot
   server event now; AI model / runtime converter later) hands us
   {source, sentence, audio_url, …} and we set the Final Sentence,
   speak it fast and log it. Sources arrive two ways:

     - `pipelineListeners` frames carrying `data.speech_event`
     - window.MovaSpeech.speak(payload) — future layers call this
       directly instead of touching hundreds of lines here

   A payload WITH audio_url plays the pre-baked file instantly.
   One WITHOUT it (e.g. future TTS converter output) shows the
   sentence immediately; synthesizing audio is that layer's job —
   call window.MovaSpeech.playAudio(url) (or swap the audio state)
   once its blob/file is ready.
   ============================================================ */

const speechState = {
  history: [],        // newest last; rendered newest-first
  current: null,      // {source?, sentence, audio_url?}
  audio: null,        // HTMLAudioElement currently playing
  speaking: false,
};

const speechEls = {
  sentence: $('pgSpeechSentence'),
  copy: $('pgSpeechCopy'),
  speak: $('pgSpeakBtn'),
  wave: $('pgWave'),
  status: $('pgSpeechStatus'),
  stop: $('pgSpeechStop'),
  history: $('pgSpeechHistory'),
  clear: $('pgSpeechClear'),
};

function setSpeechSpeaking(on) {
  speechState.speaking = on;
  speechEls.wave.classList.toggle('is-speaking', on);
  speechEls.stop.classList.toggle('is-active', on);
  speechEls.status.textContent = on ? 'Speaking…' : (speechState.current ? 'Ready' : 'Idle');
  speechEls.speak.classList.toggle('is-live', on);
  speechEls.history.classList.toggle('is-speaking', on);
}

function setSpeechSentence(text) {
  speechEls.sentence.textContent = text || '—';
}

function stopSpeech() {
  if (speechState.audio) {
    speechState.audio.pause();
    speechState.audio.currentTime = 0;
  }
  setSpeechSpeaking(false);
}

function speakCurrent() {
  const cur = speechState.current;
  if (!cur || !cur.audio_url) return;
  playAudioUrl(cur.audio_url);
}

// Shared playback path — future layers (runtime TTS converter) can hand
// any URL / blob: URL straight here once their audio exists.
function playAudioUrl(audioUrl) {
  stopSpeech();
  const audio = new Audio(`${audioUrl}${audioUrl.includes('?') ? '&' : '?'}t=${Date.now()}`);
  speechState.audio = audio;
  audio.onended = () => setSpeechSpeaking(false);
  audio.onerror = () => {
    setSpeechSpeaking(false);
    speechEls.status.textContent = 'Audio missing — re-generate on Groups';
  };
  setSpeechSpeaking(true);
  audio.play().catch(() => setSpeechSpeaking(false));
}

function renderSpeechHistory() {
  speechEls.history.replaceChildren(...[...speechState.history].reverse().map((h, i, arr) => {
    const li = document.createElement('li');
    li.className = 'pg-speech-item';
    // only the most recent entry reads as "live past"; older ones stay dim
    if (i === 0 && speechState.speaking) li.classList.add('is-live');
    const dot = document.createElement('span');
    dot.className = 'pg-speech-dot';
    const txt = document.createElement('span');
    txt.className = 'pg-speech-text';
    txt.textContent = h.sentence;
    txt.title = `${h.gesture} · ${h.space} · ${h.time} · source: ${h.source}`;
    const meta = document.createElement('span');
    meta.className = 'pg-speech-meta';
    meta.textContent = h.time;
    li.append(dot, txt, meta);
    return li;
  }));
}

function handleSpeechEvent(ev) {
  if (!ev || !ev.sentence) return;
  speechState.current = ev;
  setSpeechSentence(ev.sentence);
  speechState.history.push({
    sentence: ev.sentence,
    gesture: ev.gesture || '?',
    space: ev.space || '?',
    source: ev.source || 'unknown',
    time: nowTime(),
  });
  if (speechState.history.length > 30) speechState.history.shift();
  renderSpeechHistory();
  if (ev.audio_url) speakCurrent();
  else setSpeechSpeaking(false);
}

// Public seam for future sentence sources (AI model, runtime converter).
// MovaSpeech.speak({source, sentence, audio_url?}) does everything the
// one-shot path does: final sentence, fast playback, history entry.
window.MovaSpeech = {
  speak: handleSpeechEvent,
  playAudio: playAudioUrl,
  state: speechState,
};

speechEls.speak.addEventListener('click', speakCurrent);
speechEls.stop.addEventListener('click', stopSpeech);
speechEls.copy.addEventListener('click', () => {
  const text = speechState.current?.sentence || speechEls.sentence.textContent || '';
  if (!text || text === '—') return;
  navigator.clipboard?.writeText(text).catch(() => {});
});
speechEls.clear.addEventListener('click', () => {
  speechState.history = [];
  renderSpeechHistory();
});

pipelineListeners.push(data => handleSpeechEvent(data.speech_event));
