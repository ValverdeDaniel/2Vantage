// Voice input through Chrome's on-device speech recognition, and nothing else (plan.md §8.17; D20; the old
// components/voice/localSpeech.js, D-065). The voice never leaves the computer: nothing is recorded, uploaded or sent
// to a speech service, and the words reach the server only when the person sends the message, like typed words.
// This is the only file under src/ that names the browser's speech API. Every function takes the window it works in
// (`env`, the page's own by default), so the Front lane drives it with a fake recognizer.
//
// - Offered only in desktop Google Chrome on a secure page whose speech API has the on-device switch (Edge's default
//   mode sends the voice to a cloud service, so it is not offered).
// - The on-device switch is set on every recognizer before it starts; one that does not keep it is never started.
// - Readiness is asked when the drawer opens, never on page load; the one-time speech-pack download starts only from
//   a click.
// - The dictation-grade model is asked for only where Chrome offers it: Chrome 155 on Windows answers `unavailable`
//   for it while the plain model is downloadable, and there install() with the quality hint resolves false and a
//   recognizer with it errors language-not-supported, so the last readiness answer decides both.

const LANG = 'en-US';
// How long a stopped recognizer may still hand over its last phrase.
export const END_GRACE_MS = 1500;
// Errors that turn voice off for the session: the on-device model cannot serve this browser.
const FATAL = new Set(['service-not-allowed', 'language-not-supported', 'network', 'not-local', 'unsupported']);

// Per window: voice turned off by a fatal error, the dictation-grade answer, and the one running dictation's stop.
const states = new WeakMap();
function stateOf(env) {
  if (!states.has(env)) states.set(env, { off: false, grade: false, active: null });
  return states.get(env);
}

function recognizerOf(env) {
  return env.SpeechRecognition || env.webkitSpeechRecognition || null;
}

/** Whether this browser can dictate on the computer at all: { supported, reason } ('insecure', 'browser', 'off'). */
export function speechSupport(env = globalThis) {
  if (stateOf(env).off) return { supported: false, reason: 'off' };
  if (!env.isSecureContext) return { supported: false, reason: 'insecure' };
  const data = env.navigator?.userAgentData;
  const chrome = Boolean(data?.brands?.some((entry) => entry.brand === 'Google Chrome'));
  if (!chrome || data?.mobile) return { supported: false, reason: 'browser' };
  const Recognizer = recognizerOf(env);
  if (!Recognizer || typeof Recognizer.available !== 'function' || !('processLocally' in Recognizer.prototype)) {
    return { supported: false, reason: 'browser' };
  }
  return { supported: true, reason: '' };
}

/**
 * Chrome's answer for the on-device model: 'available' | 'downloadable' | 'downloading' | 'unavailable'. Asks for
 * the dictation-grade model first, then the plain one, and remembers which answered for the download and the
 * recognizer.
 */
export async function speechReadiness(env = globalThis) {
  const Recognizer = recognizerOf(env);
  const state = stateOf(env);
  if (!Recognizer || typeof Recognizer.available !== 'function') return 'unavailable';
  try {
    const answer = await Recognizer.available({ langs: [LANG], processLocally: true, quality: 'dictation' });
    if (answer !== 'unavailable') {
      state.grade = true;
      return answer;
    }
  } catch {
    // An older build may refuse the quality hint; ask again without it.
  }
  state.grade = false;
  try {
    return await Recognizer.available({ langs: [LANG], processLocally: true });
  } catch {
    return 'unavailable';
  }
}

/**
 * The one-time speech-pack download, started straight from the click: install() runs before the first await, inside
 * the click's activation. Resolves 'installed' or 'failed' (Chrome's false, or a refusal) once the download ends;
 * typing works throughout.
 */
export function startSpeechInstall(env = globalThis) {
  const Recognizer = recognizerOf(env);
  if (!Recognizer || typeof Recognizer.install !== 'function') return Promise.resolve('failed');
  const settle = (promise) => Promise.resolve(promise).then((ok) => (ok ? 'installed' : 'failed'));
  const plain = () => settle(Recognizer.install({ langs: [LANG], processLocally: true })).catch(() => 'failed');
  if (!stateOf(env).grade) return plain();
  return settle(Recognizer.install({ langs: [LANG], processLocally: true, quality: 'dictation' })).then(
    (result) => (result === 'installed' ? result : plain()),
    plain,
  );
}

/** A fatal error: the on-device model cannot serve here, and voice is off for the rest of the session. */
export function isFatalSpeechError(code) {
  return FATAL.has(code);
}

/**
 * Starts dictation and returns its stop function. Finished phrases go to onFinal (trimmed, never empty), the phrase
 * still being heard to onInterim ('' once it ends); onEnd is called once, however it ends; onError gets the
 * recognizer's code (a fatal one turns voice off for the session). One unexpected end restarts it once; a second ends
 * it and keeps the words.
 *
 * Chrome 155's on-device recognizer fires audioend on stop() but never end (nor after abort()), and an error need not
 * be followed by end either. So a stop or an error finishes here at once, a phrase still being transcribed has
 * END_GRACE_MS to land, and then abort() frees the microphone.
 */
export function startLocalDictation({ onInterim, onFinal, onEnd, onError }, env = globalThis) {
  const state = stateOf(env);
  const fail = (code) => {
    if (isFatalSpeechError(code)) state.off = true;
    onError?.(code);
  };
  const Recognizer = recognizerOf(env);
  if (!Recognizer) {
    fail('unsupported');
    onEnd?.();
    return () => {};
  }
  const r = new Recognizer();
  r.processLocally = true;
  if (r.processLocally !== true) {
    fail('not-local');
    onEnd?.();
    return () => {};
  }
  r.lang = LANG;
  r.continuous = true;
  r.interimResults = true;
  if (state.grade && 'quality' in Recognizer.prototype) r.quality = 'dictation';

  let stopped = false;
  let finished = false;
  let restarts = 0;
  const finish = () => {
    if (finished) return;
    finished = true;
    stopped = true;
    if (state.active === stop) state.active = null;
    onInterim?.('');
    onEnd?.();
    setTimeout(() => {
      try {
        r.abort();
      } catch {
        // Already ended.
      }
    }, END_GRACE_MS);
  };
  function stop() {
    stopped = true;
    try {
      r.stop();
    } catch {
      // Already stopped.
    }
    finish();
  }
  r.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result.isFinal) {
        const text = result[0].transcript.trim();
        if (text) onFinal?.(text);
      } else {
        interim += result[0].transcript;
      }
    }
    if (!finished) onInterim?.(interim);
  };
  r.onerror = (event) => {
    if (finished) return;
    fail(event.error);
    finish();
  };
  r.onend = () => {
    if (finished) return;
    if (!stopped && restarts < 1) {
      restarts += 1;
      try {
        r.start();
        return;
      } catch {
        // Could not restart: end below and keep what was said.
      }
    }
    finish();
  };
  try {
    r.start();
  } catch {
    fail('not-started');
    finish();
    return () => {};
  }
  state.active = stop;
  return stop;
}

/** Stops whichever dictation is running (there is only ever one). True when one was: Escape then stops the mic. */
export function stopActiveDictation(env = globalThis) {
  const state = stateOf(env);
  if (!state.active) return false;
  const stop = state.active;
  state.active = null;
  stop();
  return true;
}

/** A dictated phrase added to the composer's words, after a space unless they end in one (the old ScanChat). */
export function appendPhrase(draft, phrase) {
  if (!phrase) return draft;
  if (!draft) return phrase;
  return /\s$/.test(draft) ? `${draft}${phrase}` : `${draft} ${phrase}`;
}
