// Slice 66's "done when" (plan.md §13.10 row 66; D20, D4, D19): the microphone dictates into the composer. There is no
// real microphone here: before the app loads, the walk gives the page a fake of Chrome's on-device recognizer (its
// SpeechRecognition shape: the processLocally switch, available() and install()), then makes it "hear" words. On
// GD1's Advisor, Work with Claude shows the mic beside Send; the first click downloads the speech model once; a click
// dictates: the phrase being heard shows in grey, each finished phrase lands in the composer, a second dictation adds
// to the words, Escape stops the mic before it closes the drawer. Nothing is sent: the walk never presses Send, and no
// request carries the words or writes anything. Run with `--need s66`; it calls no Claude and changes no data.

const WORDS = 'Show the PPO quotes under $40,000 a month.';
const MORE = 'Keep the HSA plans.';

// Runs in the page before the app (serialised by addInitScript): Chrome 139+'s on-device API, faked, with
// window.__walkSpeech to make it hear words. The speech pack starts "downloadable" and installs in a second.
function fakeRecognizer() {
  const speech = { current: null, readiness: 'downloadable', installs: 0, starts: 0, stops: 0 };
  const result = (text, isFinal) => Object.assign([{ transcript: text, confidence: 0.9 }], { isFinal });
  class WalkSpeechRecognition {
    constructor() {
      this.local = false;
      this.finals = [];
      speech.current = this;
    }
    get processLocally() {
      return this.local;
    }
    set processLocally(value) {
      this.local = value === true;
    }
    start() {
      speech.starts += 1;
    }
    stop() {
      speech.stops += 1;
    }
    abort() {}
    static async available() {
      return speech.readiness;
    }
    static install() {
      speech.installs += 1;
      speech.readiness = 'downloading';
      return new Promise((resolve) => {
        setTimeout(() => {
          speech.readiness = 'available';
          resolve(true);
        }, 1000);
      });
    }
  }
  WalkSpeechRecognition.prototype.quality = '';
  speech.hear = (text) => {
    const r = speech.current;
    r.onresult?.({ resultIndex: r.finals.length, results: [...r.finals, result(text, false)] });
  };
  speech.say = (text) => {
    const r = speech.current;
    r.finals.push(result(text, true));
    r.onresult?.({ resultIndex: r.finals.length - 1, results: [...r.finals] });
  };
  for (const name of ['SpeechRecognition', 'webkitSpeechRecognition']) {
    Object.defineProperty(window, name, { value: WalkSpeechRecognition, configurable: true, writable: true });
  }
  window.__walkSpeech = speech;
}

export const voice66 = {
  title: 'Dictate into Work with Claude (a fake on-device recognizer): interim words show, finished ones land, nothing is sent',
  deal: 'GD1',
  async run(ctx, { signIn, openDeal }) {
    const { page, step } = ctx;
    await page.addInitScript(fakeRecognizer);
    const drawer = page.getByRole('dialog', { name: 'Work with Claude' });
    const box = drawer.getByLabel('Message to Claude');
    const mic = drawer.getByRole('button', { name: 'Dictate a message' });
    const stopMic = drawer.getByRole('button', { name: 'Stop dictating' });
    const said = (words) => drawer.getByRole('status').filter({ hasText: words });
    const speech = (what, text) => page.evaluate(([fn, words]) => window.__walkSpeech[fn](words), [what, text]);
    const facts = () => page.evaluate(() => ({ ...window.__walkSpeech, local: window.__walkSpeech.current?.local }));
    const holds = async (words) => {
      for (let tries = 0; tries < 50 && (await box.inputValue()) !== words; tries += 1) await page.waitForTimeout(100);
      const value = await box.inputValue();
      if (value !== words) throw new Error(`the composer holds "${value}"`);
    };
    const sent = [];
    await signIn(ctx);
    await openDeal(ctx);
    await step('the Advisor opens, and Work with Claude shows the mic beside Send', async () => {
      await page.getByRole('link', { name: 'Advisor', exact: true }).click();
      await page.getByRole('button', { name: 'Work with Claude' }).click();
      await box.waitFor();
      await mic.waitFor();
      await drawer.getByRole('button', { name: 'Send', exact: true }).waitFor();
      page.on('request', (req) => sent.push({ method: req.method(), url: req.url(), body: req.postData() || '' }));
    });
    await step("the first click downloads Chrome's speech model once, and the mic says when it is ready", async () => {
      await mic.click();
      await said("Downloading Chrome's speech model… You can type meanwhile.").waitFor();
      await said('Voice is ready: click the mic to dictate.').waitFor();
      if ((await facts()).installs !== 1) throw new Error('the speech model was not downloaded exactly once');
    });
    await step('a click starts dictating, on the computer only (processLocally)', async () => {
      await mic.click();
      await said('Listening… click to stop').waitFor();
      if ((await stopMic.getAttribute('aria-pressed')) !== 'true') throw new Error('the mic is not shown as on');
      const now = await facts();
      if (now.starts !== 1 || now.local !== true) throw new Error(`started ${now.starts}, on the computer: ${now.local}`);
    });
    await step('the phrase being heard shows in grey under the mic, and not yet in the composer', async () => {
      await speech('hear', 'show the PPO');
      await said('show the PPO').waitFor();
      await speech('hear', 'show the PPO quotes under forty thousand');
      await said('show the PPO quotes under forty thousand').waitFor();
      if ((await box.inputValue()) !== '') throw new Error('the words being heard went into the composer');
    });
    await step('the finished phrase lands in the composer', async () => {
      await speech('say', WORDS);
      await holds(WORDS);
    });
    await step('clicking the mic again stops it; the words stay in the composer, unsent', async () => {
      await stopMic.click();
      await mic.waitFor();
      await said('Listening').waitFor({ state: 'detached' });
      await holds(WORDS);
      if ((await facts()).stops !== 1) throw new Error('the recognizer was not stopped');
    });
    await step('a second dictation adds its phrase after the words already there', async () => {
      await mic.click();
      await said('Listening… click to stop').waitFor();
      await speech('say', MORE);
      await holds(`${WORDS} ${MORE}`);
    });
    await step('Escape stops the mic first and keeps the drawer open; a second Escape closes it', async () => {
      await page.keyboard.press('Escape');
      await mic.waitFor();
      await box.waitFor();
      await page.keyboard.press('Escape');
      await drawer.waitFor({ state: 'detached' });
    });
    await step('nothing left the page: no request carried the words, and nothing was sent or written', async () => {
      const carried = sent.filter((req) => [WORDS, MORE, 'PPO quotes'].some((w) => req.url.includes(w) || req.body.includes(w)));
      const writes = sent.filter((req) => req.method !== 'GET' && /\/api\//.test(req.url));
      if (carried.length) throw new Error(`the words went to ${carried.map((req) => req.url).join(', ')}`);
      if (writes.length) throw new Error(`writes while dictating: ${writes.map((req) => `${req.method} ${req.url}`).join(', ')}`);
    });
  },
};
