import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  END_GRACE_MS,
  appendPhrase,
  isFatalSpeechError,
  speechReadiness,
  speechSupport,
  startLocalDictation,
  startSpeechInstall,
  stopActiveDictation,
} from './localSpeech';

// A window with Chrome's on-device recognizer, faked: `answers` are its available() replies by quality, `installs`
// its install() replies, `keepsLocal` false for a browser that drops the on-device switch.
function fakeWindow({ answers = {}, installs = {}, keepsLocal = true, brand = 'Google Chrome', mobile = false } = {}) {
  const made = [];
  const asked = [];
  const installed = [];
  class FakeRecognition {
    constructor() {
      this.starts = 0;
      this.stops = 0;
      this.aborts = 0;
      made.push(this);
    }
    get processLocally() {
      return this.local ?? false;
    }
    set processLocally(value) {
      this.local = keepsLocal ? value : false;
    }
    start() {
      this.starts += 1;
    }
    stop() {
      this.stops += 1;
    }
    abort() {
      this.aborts += 1;
    }
    static async available(options) {
      asked.push(options);
      const answer = answers[options.quality || 'plain'] ?? 'unavailable';
      if (answer instanceof Error) throw answer;
      return answer;
    }
    static async install(options) {
      installed.push(options);
      const answer = installs[options.quality || 'plain'] ?? true;
      if (answer instanceof Error) throw answer;
      return answer;
    }
  }
  FakeRecognition.prototype.quality = '';
  const env = {
    isSecureContext: true,
    navigator: {
      userAgentData: { brands: [{ brand: 'Chromium' }, { brand }], mobile },
      mediaDevices: { getUserMedia: vi.fn() },
    },
    fetch: vi.fn(),
    webkitSpeechRecognition: FakeRecognition,
  };
  return { env, made, asked, installed };
}

// What a recognizer hands over: results from `from` on, each { text, final }.
function heard(items, from = 0) {
  const results = items.map(({ text, final = false }) => Object.assign([{ transcript: text }], { isFinal: final }));
  return { resultIndex: from, results };
}

function listener() {
  const log = { interim: [], finals: [], ends: 0, errors: [] };
  return {
    log,
    onInterim: (text) => log.interim.push(text),
    onFinal: (text) => log.finals.push(text),
    onEnd: () => {
      log.ends += 1;
    },
    onError: (code) => log.errors.push(code),
  };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('where voice is offered (D20)', () => {
  it('offers the mic in desktop Chrome on a secure page whose recognizer can run on the computer', () => {
    expect(speechSupport(fakeWindow().env)).toEqual({ supported: true, reason: '' });
  });

  it('keeps it away from insecure pages, other browsers, phones and recognizers without the on-device switch', () => {
    expect(speechSupport({ ...fakeWindow().env, isSecureContext: false }).reason).toBe('insecure');
    expect(speechSupport(fakeWindow({ brand: 'Microsoft Edge' }).env).reason).toBe('browser');
    expect(speechSupport(fakeWindow({ mobile: true }).env).reason).toBe('browser');
    const cloudOnly = fakeWindow().env;
    cloudOnly.webkitSpeechRecognition = class CloudOnly {};
    expect(speechSupport(cloudOnly).reason).toBe('browser');
    expect(speechSupport({ isSecureContext: true, navigator: {} }).supported).toBe(false);
  });

  it('asks for the dictation-grade model first and falls back to the plain one', async () => {
    const graded = fakeWindow({ answers: { dictation: 'available' } });
    expect(await speechReadiness(graded.env)).toBe('available');
    expect(graded.asked).toEqual([{ langs: ['en-US'], processLocally: true, quality: 'dictation' }]);

    const plain = fakeWindow({ answers: { dictation: 'unavailable', plain: 'downloadable' } });
    expect(await speechReadiness(plain.env)).toBe('downloadable');
    expect(plain.asked.at(-1)).toEqual({ langs: ['en-US'], processLocally: true });

    const older = fakeWindow({ answers: { dictation: new TypeError('quality'), plain: 'downloading' } });
    expect(await speechReadiness(older.env)).toBe('downloading');
    expect(await speechReadiness(fakeWindow({ answers: { plain: new Error('no') } }).env)).toBe('unavailable');
  });
});

describe('the one-time speech-pack download (D20)', () => {
  it('installs the model readiness found, and falls back to the plain one when the graded download fails', async () => {
    const graded = fakeWindow({ answers: { dictation: 'downloadable' }, installs: { dictation: false } });
    await speechReadiness(graded.env);
    expect(await startSpeechInstall(graded.env)).toBe('installed');
    expect(graded.installed.map((options) => options.quality || 'plain')).toEqual(['dictation', 'plain']);

    const plain = fakeWindow({ answers: { plain: 'downloadable' } });
    await speechReadiness(plain.env);
    expect(await startSpeechInstall(plain.env)).toBe('installed');
    expect(plain.installed).toEqual([{ langs: ['en-US'], processLocally: true }]);
  });

  it("says 'failed' when Chrome answers false, refuses, or has no install()", async () => {
    expect(await startSpeechInstall(fakeWindow({ installs: { plain: false } }).env)).toBe('failed');
    expect(await startSpeechInstall(fakeWindow({ installs: { plain: new Error('quota') } }).env)).toBe('failed');
    const noInstall = fakeWindow().env;
    noInstall.webkitSpeechRecognition = class Old {};
    expect(await startSpeechInstall(noInstall)).toBe('failed');
  });
});

describe('dictating (D20)', () => {
  it('runs on the computer only, continuous, with the words still being heard', () => {
    const { env, made } = fakeWindow();
    const stop = startLocalDictation(listener(), env);
    const [r] = made;
    expect([r.processLocally, r.lang, r.continuous, r.interimResults, r.starts]).toEqual([true, 'en-US', true, true, 1]);
    expect(r.quality).toBe('');
    stop();
  });

  it('asks for dictation grade only where readiness found it', async () => {
    const { env, made } = fakeWindow({ answers: { dictation: 'available' } });
    await speechReadiness(env);
    startLocalDictation(listener(), env)();
    expect(made[0].quality).toBe('dictation');
  });

  it('shows the phrase being heard and hands over each finished phrase, trimmed', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    startLocalDictation(handlers, env);
    const [r] = made;
    r.onresult(heard([{ text: 'show the' }]));
    r.onresult(heard([{ text: 'show the PPO quotes' }]));
    r.onresult(heard([{ text: ' Show the PPO quotes. ', final: true }, { text: 'under' }]));
    r.onresult(heard([{ text: 'x', final: true }, { text: '   ', final: true }, { text: 'under forty' }], 1));
    expect(log.interim).toEqual(['show the', 'show the PPO quotes', 'under', 'under forty']);
    expect(log.finals).toEqual(['Show the PPO quotes.']);
    expect(log.ends).toBe(0);
  });

  it('a stop ends at once, lets the last phrase land, then frees the microphone', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    const stop = startLocalDictation(handlers, env);
    const [r] = made;
    r.onresult(heard([{ text: 'under forty thousand' }]));
    stop();
    expect([r.stops, log.ends, log.interim.at(-1)]).toEqual([1, 1, '']);
    r.onresult(heard([{ text: 'under forty thousand a month', final: true }, { text: 'late' }]));
    expect(log.finals).toEqual(['under forty thousand a month']);
    expect(log.interim.at(-1)).toBe('');
    expect(r.aborts).toBe(0);
    vi.advanceTimersByTime(END_GRACE_MS);
    expect(r.aborts).toBe(1);
    stop();
    r.onend();
    expect(log.ends).toBe(1);
  });

  it('restarts once after an unexpected end, and keeps the words after a second', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    startLocalDictation(handlers, env);
    const [r] = made;
    r.onresult(heard([{ text: 'hello', final: true }]));
    r.onend();
    expect([r.starts, log.ends]).toEqual([2, 0]);
    r.onend();
    expect([r.starts, log.ends, log.finals]).toEqual([2, 1, ['hello']]);
  });

  it('a blocked microphone ends the dictation and says so, but keeps voice on', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    startLocalDictation(handlers, env);
    made[0].onerror({ error: 'not-allowed' });
    made[0].onerror({ error: 'aborted' });
    expect([log.errors, log.ends]).toEqual([['not-allowed'], 1]);
    expect(isFatalSpeechError('not-allowed')).toBe(false);
    expect(speechSupport(env).supported).toBe(true);
  });

  it('turns voice off for the session when the on-device model cannot serve', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    startLocalDictation(handlers, env);
    made[0].onerror({ error: 'service-not-allowed' });
    expect([log.errors, log.ends]).toEqual([['service-not-allowed'], 1]);
    expect(speechSupport(env)).toEqual({ supported: false, reason: 'off' });
  });

  it('never starts a recognizer that drops the on-device switch', () => {
    const { env, made } = fakeWindow({ keepsLocal: false });
    const { log, ...handlers } = listener();
    startLocalDictation(handlers, env)();
    expect([made[0].starts, log.errors, log.ends]).toEqual([0, ['not-local'], 1]);
    expect(speechSupport(env).reason).toBe('off');
  });

  it('records and sends nothing: no microphone stream, no request', () => {
    const { env, made } = fakeWindow();
    const stop = startLocalDictation(listener(), env);
    made[0].onresult(heard([{ text: 'a secret', final: true }]));
    stop();
    vi.advanceTimersByTime(END_GRACE_MS);
    expect(env.fetch).not.toHaveBeenCalled();
    expect(env.navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled();
  });
});

describe('one dictation at a time (D4, D19, D20)', () => {
  it('Escape or Send stops the running dictation, and says whether one ran', () => {
    const { env, made } = fakeWindow();
    const { log, ...handlers } = listener();
    expect(stopActiveDictation(env)).toBe(false);
    startLocalDictation(handlers, env);
    expect(stopActiveDictation(env)).toBe(true);
    expect([made[0].stops, log.ends]).toEqual([1, 1]);
    expect(stopActiveDictation(env)).toBe(false);
  });

  it('a dictation that ended by itself is no longer the running one', () => {
    const { env, made } = fakeWindow();
    startLocalDictation(listener(), env);
    made[0].onerror({ error: 'no-speech' });
    expect(stopActiveDictation(env)).toBe(false);
  });
});

describe('dictated words join the composer (D19, D20)', () => {
  it('adds each phrase after a space, unless the words end in one', () => {
    expect(appendPhrase('', 'Show the PPOs')).toBe('Show the PPOs');
    expect(appendPhrase('Show the PPOs', 'under $40,000')).toBe('Show the PPOs under $40,000');
    expect(appendPhrase('First line\n', 'second')).toBe('First line\nsecond');
    expect(appendPhrase('Kept', '')).toBe('Kept');
  });
});
