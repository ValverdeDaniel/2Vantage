import { useEffect, useRef, useState } from 'react';
import {
  isFatalSpeechError,
  speechReadiness,
  speechSupport,
  startLocalDictation,
  startSpeechInstall,
} from './localSpeech';

/*
 * The mic beside the composer (plan.md §8.17; D20, simplified from the old components/voice/MicButton): click to
 * dictate, click again to stop. Each finished phrase goes to onPhrase (the composer adds it to its words); the phrase
 * still being heard shows in grey under "Listening… click to stop". Shown only where Chrome can dictate on this
 * computer, and asked when the drawer opens. On a computer without Chrome's speech pack the first click starts its
 * one-time download and the mic says when it is ready; the old setup, progress and help cards are gone (D20). A fatal
 * error hides the mic for the session. Nothing is recorded or sent: the words reach Claude only on Send.
 */

const MESSAGES = {
  'not-allowed': "Microphone blocked — allow it for this site in Chrome's address bar.",
  'no-speech': "I didn't hear anything — click the mic.",
};
const DOWNLOADING = "Downloading Chrome's speech model… You can type meanwhile.";
const READY = 'Voice is ready: click the mic to dictate.';
const FAILED = "Chrome couldn't download its speech model. Click the mic to try again.";

function MicGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2Z"
      />
    </svg>
  );
}

export default function MicButton({ onPhrase, label = 'Dictate' }) {
  const [off, setOff] = useState(() => !speechSupport().supported);
  const [readiness, setReadiness] = useState(null);
  const [listening, setListening] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [interim, setInterim] = useState('');
  const [message, setMessage] = useState('');
  const stopRef = useRef(null);
  const live = useRef(true);

  useEffect(() => {
    live.current = true;
    if (off) return undefined;
    speechReadiness().then((state) => {
      if (live.current) setReadiness(state);
    });
    return () => {
      live.current = false;
      stopRef.current?.();
    };
  }, [off]);

  // Unavailable from the first answer hides the mic; after a click it stays, to say how the download went.
  if (off || readiness === null || (readiness === 'unavailable' && !installing && !message)) return null;

  const start = () => {
    setListening(true);
    stopRef.current = startLocalDictation({
      onInterim: setInterim,
      onFinal: onPhrase,
      onEnd: () => {
        setListening(false);
        setInterim('');
        stopRef.current = null;
      },
      onError: (code) => {
        if (isFatalSpeechError(code)) setOff(true);
        else setMessage(MESSAGES[code] || '');
      },
    });
  };

  // From the click itself: install() needs its activation.
  const install = () => {
    const download = startSpeechInstall();
    setInstalling(true);
    setMessage(DOWNLOADING);
    download.then(async (result) => {
      const state = await speechReadiness();
      if (!live.current) return;
      setReadiness(state);
      setInstalling(false);
      setMessage(result === 'installed' && state === 'available' ? READY : FAILED);
    });
  };

  const click = () => {
    if (listening) {
      stopRef.current?.();
      return;
    }
    setMessage('');
    if (readiness === 'available') start();
    else install();
  };

  return (
    <span className="hlp-mic-wrap">
      <button
        type="button"
        className={`hlp-mic${listening ? ' hlp-mic--on' : ''}`}
        aria-pressed={listening}
        aria-label={listening ? 'Stop dictating' : label}
        title={listening ? 'Listening… click to stop' : 'Dictate (your voice stays on this computer)'}
        onClick={click}
        disabled={installing}
      >
        <MicGlyph />
      </button>
      {(listening || message) && (
        <span className="hlp-mic-pop" role="status">
          {listening ? (
            <>
              Listening… click to stop
              {interim && <span className="hlp-mic-interim"> {interim}</span>}
            </>
          ) : (
            message
          )}
        </span>
      )}
    </span>
  );
}
