"""The Claude client (plan.md §10.3; D.6, O.3.3, OQ29): the only module that imports `anthropic`.

- The Messages API only: no beta features, no Files API, no token counting; files go base64 in each request.
- `request()` builds one structured-output call (`output_config.format`, 128k `max_tokens`, adaptive thinking, the
  effort for its kind). The prompt is one system block marked for the cache, byte-identical across deals; the files
  and the per-call note follow in the user turn. No temperature, no prefill, no forced tool choice.
- `transport()` sends it, streamed. Every stream event calls `on_event` (the job's beat: Stop raises there and the
  stream closes); a call also has a read timeout (silence) and a wall-clock cap. A client is built only from
  `settings.ANTHROPIC_API_KEY`, passed explicitly, so the SDK never falls back to an environment variable or an `ant`
  profile; with no key there is no client (`NoKey`). Tests install the fake transport of `ai/testing.py`.
- `check()` turns a reply into its data, or raises: `Truncated` (the output hit `max_tokens`: the range halves),
  `Refused` (`stop_reason` refusal: one retry on the other of Sonnet 5.5 and Opus 5.5, where allowed). `AccountError`
  stops a run; `CallFailed` is one failed part. Every error carries what the call used so far (`seen`), so it is
  recorded and priced even when it ends early. Errors say a fixed sentence: never the API's text, which can quote a
  file.
"""

import json
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings

logger = logging.getLogger(__name__)

MAX_TOKENS = 128_000
CONNECT_SECONDS = 10.0
READ_SECONDS = 180.0  # a stream silent this long has hung (pings arrive every few seconds)
WALL_SECONDS = 20 * 60.0  # one call may not run longer than this
OUTPUT_CHARS_PER_TOKEN = 3  # a stopped stream's output, counted from what arrived (on the high side)


class ClaudeError(Exception):
    sentence = 'Claude could not answer.'
    reason = 'error'

    def __init__(self, sentence=None, *, seen=None):
        super().__init__(sentence or self.sentence)
        self.sentence = sentence or self.sentence
        self.seen = seen  # Reply or None: what the call used before it ended


class NoKey(ClaudeError):
    sentence = 'Claude is not set up on this server, so nothing can be read.'
    reason = 'no_key'


class AccountError(ClaudeError):
    sentence = "Claude's account refused the call (its key, permissions or credit), so this stopped. Tell an admin."
    reason = 'account'


class CallFailed(ClaudeError):
    sentence = 'Claude did not answer this part (busy, offline or too slow).'
    reason = 'error'


class Truncated(ClaudeError):
    sentence = 'The answer for this part was longer than one call may write.'
    reason = 'truncated'


class Refused(ClaudeError):
    sentence = 'Claude declined to read this part.'
    reason = 'refused'


@dataclass
class Reply:
    model: str
    usage: dict = field(default_factory=dict)
    stop_reason: str = ''
    text: str = ''
    partial: bool = False


def available():
    """Whether Claude can be called here: a key is set, or a test installed the fake."""
    return _installed is not None or bool(settings.ANTHROPIC_API_KEY)


def request(*, model, system, content, schema, effort, max_tokens=MAX_TOKENS):
    """The params of one structured-output call. `content` is the user turn's blocks (files, then the note)."""
    return {
        'model': model,
        'max_tokens': max_tokens,
        'system': [{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
        'messages': [{'role': 'user', 'content': content}],
        'thinking': {'type': 'adaptive'},
        'output_config': {'effort': effort, 'format': {'type': 'json_schema', 'schema': schema}},
    }


def check(reply):
    """The reply's data (parsed JSON), or Truncated / Refused / CallFailed."""
    if reply.stop_reason == 'max_tokens':
        raise Truncated(seen=reply)
    if reply.stop_reason == 'refusal':
        raise Refused(seen=reply)
    try:
        return json.loads(reply.text)
    except (TypeError, ValueError):
        raise CallFailed('Claude answered this part in a form that could not be read.', seen=reply) from None


def _usage(usage):
    if usage is None:
        return {}
    keys = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
    return {key: int(getattr(usage, key, 0) or 0) for key in keys}


class Live:
    """The real transport: Anthropic's SDK, streamed."""

    def __init__(self, api_key):
        import anthropic

        self._sdk = anthropic
        self._client = anthropic.Anthropic(
            api_key=api_key,
            max_retries=2,
            timeout=anthropic.Timeout(READ_SECONDS, connect=CONNECT_SECONDS),
            open_telemetry=False,
        )

    def _error(self, exc, seen):
        sdk = self._sdk
        if isinstance(exc, (sdk.AuthenticationError, sdk.PermissionDeniedError)):
            return AccountError(seen=seen)
        if isinstance(exc, sdk.BadRequestError) and 'credit' in str(getattr(exc, 'message', '')).lower():
            return AccountError(seen=seen)
        if isinstance(exc, sdk.APIError):
            return CallFailed(seen=seen)
        return None

    def send(self, params, *, key=None, on_event=None):
        """One streamed call. `key` names the call for the fake (reader, file hash, range); unused here."""
        seen = Reply(model=params['model'], partial=True)
        chars = 0
        started = time.monotonic()
        try:
            with self._client.messages.stream(**params) as stream:
                for event in stream:
                    if event.type == 'message_start':
                        seen.model = event.message.model or seen.model
                        seen.usage = _usage(event.message.usage)
                    elif event.type == 'content_block_delta':
                        delta = event.delta
                        chars += len(getattr(delta, 'text', None) or getattr(delta, 'thinking', None) or '')
                        seen.usage['output_tokens'] = chars // OUTPUT_CHARS_PER_TOKEN + 1
                    if on_event:
                        on_event()
                    if time.monotonic() - started > WALL_SECONDS:
                        raise CallFailed('Claude took too long on this part.', seen=seen)
                message = stream.get_final_message()
        except ClaudeError:
            raise
        except Exception as exc:
            mapped = self._error(exc, seen)
            if mapped is None:
                exc.seen = seen  # Stopped, Paused, Gone: the caller records what was used, then lets it go
                raise
            logger.warning('A Claude call failed: %s', exc.__class__.__name__)  # the class only, never its text
            raise mapped from None
        text = ''.join(block.text for block in message.content if block.type == 'text')
        return Reply(model=message.model, usage=_usage(message.usage), stop_reason=message.stop_reason or '', text=text)


_installed = None
_live = {}


def install(fake):
    """Use `fake` (ai.testing.FakeTransport) for every call until `install(None)`. Returns the one it replaced."""
    global _installed
    previous, _installed = _installed, fake
    return previous


def transport():
    """The fake a test installed, else the live client; NoKey without `settings.ANTHROPIC_API_KEY`."""
    if _installed is not None:
        return _installed
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise NoKey
    if api_key not in _live:
        _live.clear()
        _live[api_key] = Live(api_key)
    return _live[api_key]
