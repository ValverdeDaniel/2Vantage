import { useState } from 'react';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import MicButton from '../../voice/MicButton';
import { appendPhrase, stopActiveDictation } from '../../voice/localSpeech';
import { placeholder } from './chatWords';

/*
 * The composer (plan.md §8.17; D19, D20, D104; the old ScanChat input): Enter sends, Shift+Enter starts a new line;
 * Send waits while Claude answers (one turn runs per deal); the placeholder says when the table is locked from Claude.
 * The words stay if sending fails. The mic beside Send adds each dictated phrase to the words, which stay here, like
 * typed ones, until Send; Send (or Enter) while dictating stops the mic and sends the finished words, and a phrase
 * still landing stays for the next message.
 */
export default function Composer({ chat, locked }) {
  const toast = useToast();
  const [draft, setDraft] = useState('');
  const busy = chat.busy;

  async function send() {
    stopActiveDictation();
    const text = draft.trim();
    if (!text || busy) return;
    try {
      await chat.send(text);
      setDraft((current) => (current.startsWith(draft) ? current.slice(draft.length).trimStart() : ''));
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <>
      <textarea
        rows={2}
        value={draft}
        aria-label="Message to Claude"
        placeholder={placeholder({ locked, busy: Boolean(chat.running) })}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            send();
          }
        }}
      />
      <div className="bnf-scanchat-send">
        <MicButton onPhrase={(phrase) => setDraft((current) => appendPhrase(current, phrase))} label="Dictate a message" />
        <button type="button" className="btn btn-primary btn-sm" onClick={send} disabled={busy || !draft.trim()}>
          Send
        </button>
      </div>
    </>
  );
}
