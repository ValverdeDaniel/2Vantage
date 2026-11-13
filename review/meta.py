"""Review's vocabularies for /api/meta/ as `review` (rule 1; plan.md §7.1): the security levels, request and link
states, close reasons, the readiness chip's words, the fixed link rules (OQ81, OQ83: code constants), and the review
queue's words: what an answer did, its phases, the queue's sections and the idle hours (slice 55); a note's kinds, the
request page's statuses and tabs and the tray's sections (slice 56); where a value came from, the boards' rules,
statuses and bar segments (slice 57)."""

from census import fields as census_fields

from . import origins, words
from .rules import asks, items, policy


def _pairs(choices):
    return [{'key': key, 'label': label} for key, label in choices]


def meta():
    return {
        'levels': words.LEVELS,
        'level_needs': words.LEVEL_NEEDS,
        'request_states': _pairs(words.REQUEST_STATES),
        'link_states': _pairs(words.LINK_STATES),
        'close_reasons': _pairs(words.CLOSE_REASONS),
        'readiness': _pairs(words.READINESS),
        'intake_scopes': _pairs(words.INTAKE_SCOPES),
        'census_scopes': _pairs(words.CENSUS_SCOPES),
        'document_kinds': list(asks.DOCUMENT_KINDS),
        'life_days': policy.LIFE_DAYS,
        'ceiling_days': policy.CEILING_DAYS,
        'expiring_days': policy.EXPIRING_DAYS,
        'pin_digits': policy.PIN_DIGITS,
        'message_limit': policy.MESSAGE_LIMIT,
        'max_people': policy.MAX_PEOPLE,
        'changes': _pairs(words.CHANGES),
        'phases': [{'key': key, 'label': label, 'title': title} for key, label, title in words.PHASES],
        'queue_sections': _pairs(words.QUEUE_SECTIONS),
        'idle_hours': int(items.IDLE.total_seconds() // 3600),
        'note_kinds': _pairs(words.NOTE_KINDS),
        'rail_statuses': _pairs(words.RAIL_STATUSES),
        'tray_sections': _pairs(words.TRAY_SECTIONS),
        'request_panes': _pairs(words.REQUEST_PANES),
        'note_limit': 1000,
        'origins': origins.ORIGINS,
        'next_kinds': _pairs(words.NEXT_KINDS),
        'rules': _pairs(words.RULES),
        'intake_rules': _pairs(words.INTAKE_RULES),
        'board_statuses': _pairs(words.BOARD_STATUSES),
        'census_segments': _pairs(words.CENSUS_SEGMENTS),
        'census_groups': _pairs(census_fields.GROUPS),
        'note_rule_limit': 300,
        'enter_limit': 500,
        'file_hint': 400,
    }
