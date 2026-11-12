"""What a Claude call costs (plan.md §10.3; D.6, D53; the old docscan/pricing.py with B17's mistakes fixed). Pure.

Prices are dollars per million tokens, from Anthropic's list (2026-11): input, output and cache reads; a cache write
costs 1.25 times input. Haiku 5.5 has a second tier: a request whose prompt (input plus cache write and read) passes
100,000 tokens is priced at the higher one. A model not listed is priced at the top price, so a mistyped or newer
model id never makes a call look cheap. Every call is priced from the model that answered (D.6).
"""

from decimal import ROUND_HALF_UP, Decimal

SONNET = 'claude-sonnet-5-5'
OPUS = 'claude-opus-5-5'
HAIKU = 'claude-haiku-5-5'

MILLION = Decimal(1_000_000)
CACHE_WRITE = Decimal('1.25')
HAIKU_TIER_TOKENS = 100_000

# model: (input, output, cache read) per million tokens
PRICES = {
    SONNET: (Decimal('2'), Decimal('10'), Decimal('0.10')),
    OPUS: (Decimal('4'), Decimal('20'), Decimal('0.20')),
    HAIKU: (Decimal('0.10'), Decimal('0.50'), Decimal('0.01')),
}
HAIKU_ABOVE_TIER = (Decimal('0.50'), Decimal('2.50'), Decimal('0.05'))
TOP = PRICES[OPUS]

# The reading models in the order "Try again" offers them (D9, D23, D91): reads never run on Haiku.
READ_MODELS = (SONNET, OPUS)
LABELS = {SONNET: 'Sonnet 5.5', OPUS: 'Opus 5.5', HAIKU: 'Haiku 5.5'}


def _tokens(usage, key):
    return int((usage or {}).get(key) or 0)


def rates(model, prompt_tokens=0):
    """(input, output, cache read) per million tokens for `model`."""
    if model == HAIKU and prompt_tokens > HAIKU_TIER_TOKENS:
        return HAIKU_ABOVE_TIER
    return PRICES.get(model, TOP)


def cost(model, usage):
    """Dollars for one call's usage {input_tokens, output_tokens, cache_creation_input_tokens,
    cache_read_input_tokens}, to six places."""
    fresh = _tokens(usage, 'input_tokens')
    written = _tokens(usage, 'cache_creation_input_tokens')
    read = _tokens(usage, 'cache_read_input_tokens')
    out = _tokens(usage, 'output_tokens')
    price_in, price_out, price_read = rates(model, fresh + written + read)
    total = fresh * price_in + written * price_in * CACHE_WRITE + read * price_read + out * price_out
    return (total / MILLION).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def worst_case(model, input_tokens, max_tokens):
    """The most a call can cost: its whole input uncached and every output token it may write (D53's refusal rule)."""
    return cost(model, {'input_tokens': input_tokens, 'output_tokens': max_tokens})


def other_model(model):
    """The model a refused read tries once (D91): Sonnet 5.5 and Opus 5.5 each other's; anything else none."""
    return {SONNET: OPUS, OPUS: SONNET}.get(model)
