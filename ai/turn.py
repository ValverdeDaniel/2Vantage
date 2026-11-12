"""One chat turn: the `turn` job, in the chat lane (plan.md §10.6; D77–D79, D81–D83, D90, D91, D105; slice 24).

The person's message (`params.message_id`) and the chat's last 30 messages (D79) become the request; the newest
message carries the attached files (at most three, D82), the context (D78: the deal, its files, the plan table capped
at 120,000 characters and the board from quotes, the client guidance from intake, the carrier notes) and the words,
under one cache breakpoint, so every round reads them from the cache. Then up to 8 streamed rounds (D83): each is one
call with the strict tools (D81); every tool Claude calls runs in code and its answer goes back in one message (whose
last block is the next breakpoint); a round without tools is the reply. A question never waits behind a read: reads
run in the work lane.

Spending: before the first call the turn's estimate must fit the deal's budget unless overridden (D24, D99); each call
is reserved against the total cap and settled at what it used (`calls.extract`); past the run cap the turn stops
calling and says so. A refusal tries the round once on the other of Sonnet 5.5 and Opus 5.5, for admins and direct
people (D91). Stop ends the turn at the next stream event, keeping what Claude proposed so far for review.

Claude's reply becomes the chat's next message (`ChatMessage`, with the job); the change set the tools built is the
job's result, which lands by itself or waits (`services.turns.on_finish`, the kind's land hook). The board patch rides
the result for the browser (D80). Nothing here writes deal data.
"""

import json
from decimal import Decimal

from django.conf import settings

from documents.models import Document

from . import budget, calls, client, history, pricing, reading, tools, turn_files, turn_prompt
from .models import ChatMessage, DealAi, Job
from .progress import JobFailed, Stopped
from .turn_state import TurnState

MAX_ROUNDS = 8
MAX_TOKENS = 32_000
REPLY_TOKENS = 1500  # what a round is expected to write, for the estimate
CACHE = {'type': 'ephemeral'}
USAGE_KEYS = reading.USAGE_KEYS
OVER_BUDGET, STAGED = reading.OVER_BUDGET, reading.STAGED

NO_MESSAGE = 'The message this turn answers is gone.'
ROUNDS_USED = f'Claude used its {MAX_ROUNDS} rounds on this; ask again to go on.'
STOPPED = 'Stopped — what Claude proposed before Stop waits for your review.'
STOPPED_NOTHING = 'Stopped.'


def round_key(words, number):
    """What names one round of a turn for the fake client (ai.testing): the person's words and the round's number."""
    return ('turn', ' '.join(str(words).split()), int(number))


def _tokens(text):
    return int(len(text) / budget.CHARS_PER_TOKEN)


def _text_of(messages):
    """The characters of the messages' words, tool calls and tool answers (files are counted apart)."""
    total = 0
    for message in messages:
        body = message['content']
        if isinstance(body, str):
            total += len(body)
            continue
        for block in body:
            if block.get('type') in ('text', 'thinking'):
                total += len(block.get('text') or block.get('thinking') or '')
            elif block.get('type') == 'tool_use':
                total += len(json.dumps(block.get('input')))
            elif block.get('type') == 'tool_result':
                total += len(str(block.get('content') or ''))
    return total


def _uncache(messages):
    """The earlier round's breakpoint moves to the new round's answers (four breakpoints at most)."""
    for message in messages[1:]:
        if isinstance(message['content'], list) and message['content'][0].get('type') == 'tool_result':
            for block in message['content']:
                block.pop('cache_control', None)


def lands_at_once(job):
    """(lands, words for Claude): a direct person's changes land when the turn ends, unless the table is locked or the
    deal lost (D71, D104); everyone else's wait."""
    from deals import rules

    from .services.landing import is_direct

    if not is_direct(job.created_by):
        return False, turn_prompt.WAITS
    if DealAi.objects.filter(deal_id=job.deal_id, locked_at__isnull=False).exists():
        return False, turn_prompt.LOCKED
    if rules.refuses(job.deal, 'ai_land'):
        return False, turn_prompt.WAITS
    return True, turn_prompt.LANDS


class Turn:
    def __init__(self, job, progress, message):
        self.job, self.progress, self.message = job, progress, message
        self.params = job.params or {}
        self.model = reading.model_for(job)
        self.effort = settings.AI_EFFORT.get('turn', 'low')
        self.override = bool(self.params.get('budget_override'))
        self.allow_other = reading.may_use_opus(job.created_by)
        lands, self.lands_words = lands_at_once(job)
        self.state = TurnState(job, self.params.get('page'), lands)
        self.spent, self.usage, self.calls, self.rounds = Decimal(0), dict.fromkeys(USAGE_KEYS, 0), 0, 0
        self.halted, self.texts, self.switched = '', [], False

    # ---- the request ------------------------------------------------------------------------------------------------
    def messages(self):
        order = {doc_id: n for n, doc_id in enumerate(self.job.documents)}
        found = Document.objects.filter(deal_id=self.job.deal_id, pk__in=self.job.documents)
        documents = sorted(found, key=lambda doc: order[doc.id])
        blocks, self.file_tokens, said = turn_files.blocks(documents)
        rows = history.as_messages(history.window(self.job.chat_id, self.message.id))
        words = rows[-1]['content'] if rows and rows[-1]['role'] == 'user' else self.message.text
        if said:
            words += '\n\n(' + ' '.join(said) + ')'
        context = turn_prompt.context(self.job.deal, self.state.page, lands=self.lands_words)
        newest = [*blocks, {'type': 'text', 'text': context}, {'type': 'text', 'text': words, 'cache_control': CACHE}]
        earlier = rows[:-1] if rows and rows[-1]['role'] == 'user' else rows
        return [*earlier, {'role': 'user', 'content': newest}]

    def planned(self, messages, specs):
        params = client.converse(
            model=self.model,
            system=turn_prompt.PROMPT,
            tools=specs,
            messages=messages,
            effort=self.effort,
            max_tokens=MAX_TOKENS,
        )
        tokens = _tokens(turn_prompt.PROMPT + json.dumps(specs)) + self.file_tokens + _tokens('x' * _text_of(messages))
        return calls.Planned(params, round_key(self.message.text, self.rounds + 1), tokens, check=client.check_round)

    # ---- the rounds -------------------------------------------------------------------------------------------------
    def record(self, done):
        self.calls += 1
        self.spent += Decimal(done.cost or 0)
        for key in USAGE_KEYS:
            self.usage[key] += int(((done.reply.usage if done.reply else {}) or {}).get(key) or 0)

    def check_budget(self, messages, specs):
        first = self.planned(messages, specs)
        estimate = pricing.cost(self.model, {'input_tokens': first.input_tokens, 'output_tokens': REPLY_TOKENS})
        budget.check_turn(self.job.deal_id, estimate, self.override)

    def run(self):
        messages, specs = self.messages(), tools.specs()
        self.check_budget(messages, specs)
        self.progress.step('Claude is working on your message', 5)
        while self.rounds < MAX_ROUNDS:
            planned = self.planned(messages, specs)
            self.rounds += 1
            try:
                done = calls.extract(planned, job=self.job, purpose='turn', on_event=self.progress.beat)
            except budget.OverLimit as exc:
                self.halted = exc.sentence
                return
            self.record(done)
            if done.error is not None:
                if self._retry_other(done.error):
                    continue
                self._ended(done)
                return
            reply = done.data
            messages.append({'role': 'assistant', 'content': reply.content})
            if reply.text.strip():
                self.texts.append(reply.text.strip())
            uses = [block for block in reply.content if block.get('type') == 'tool_use']
            if reply.stop_reason != 'tool_use' or not uses:
                return
            messages.append({'role': 'user', 'content': self.answer(uses, messages)})
            if budget.over_run_cap(self.spent, self.override):
                self.halted = f'This turn reached its ${budget.run_cap():,.2f} cap, so Claude stopped here.'
                return
        self.halted = ROUNDS_USED

    def answer(self, uses, messages):
        results = []
        for block in uses:
            self.progress.say(f'Claude is using {block.get("name", "a tool")}', min(90, 10 + 10 * self.rounds))
            words, is_error = tools.run(self.state, block)
            result = {'type': 'tool_result', 'tool_use_id': block.get('id'), 'content': words}
            if is_error:
                result['is_error'] = True
            results.append(result)
        _uncache(messages)
        results[-1]['cache_control'] = CACHE
        return results

    def _retry_other(self, error):
        other = pricing.other_model(self.model)
        if isinstance(error, client.Refused) and self.allow_other and other and not self.switched:
            self.model, self.switched = other, True
            return True
        return False

    def _ended(self, done):
        error = done.error
        seen = done.reply.text.strip() if done.reply and done.reply.text else ''
        if seen:
            self.texts.append(seen)
        self.halted = error.sentence

    # ---- the end ----------------------------------------------------------------------------------------------------
    def reply(self):
        text = self.texts[-1] if self.texts else ''
        if self.halted:
            text = f'{text}\n\n{self.halted}'.strip()
        return text or 'Done.'

    def save_usage(self):
        Job.objects.filter(pk=self.job.pk).update(model=self.model, usage={**self.usage, 'calls': self.calls})

    def finish(self, text):
        said = ChatMessage.objects.create(chat_id=self.job.chat_id, role=ChatMessage.ASSISTANT, text=text, job=self.job)
        return self.state.result(
            reply_id=said.id,
            model=self.model,
            cost_usd=f'{self.spent:.4f}',
            rounds=self.rounds,
            partial=bool(self.halted),
            halted=self.halted,
        )


def run(job, progress):
    """The `turn` job's runner: returns the turn's change set and board (Job.result)."""
    message = ChatMessage.objects.filter(pk=(job.params or {}).get('message_id'), chat_id=job.chat_id).first()
    if message is None:
        raise JobFailed(NO_MESSAGE)
    turn = Turn(job, progress, message)
    try:
        turn.run()
    except budget.OverLimit as exc:
        Job.objects.filter(pk=job.pk).update(land=OVER_BUDGET, wait_reason=exc.sentence[:200])
        return {'v': 1, 'target': 'turn', 'over': exc.kind, 'items': [], 'board': None}
    except Stopped:
        turn.save_usage()
        said = STOPPED if turn.state.items else STOPPED_NOTHING
        progress.result = turn.finish((f'{turn.texts[-1]}\n\n' if turn.texts else '') + said)
        if turn.state.items:
            Job.objects.filter(pk=job.pk).update(land=STAGED, wait_reason=STOPPED[:200])
        raise
    turn.save_usage()
    progress.step(turn.state.summary() or 'Answered', 99)
    return turn.finish(turn.reply())
