"""The member-data screen, run at upload and stored on `Document.screen` (plan.md §3.8, §10.8; D52, O.6 #45; OQ22).

    {"version": 2, "left_out_pages": [3, 4], "image_pages": [7], "lists_members": true}

`left_out_pages` are a PDF's pages that show member data (rows of people: a roster, birth dates, SSNs, a sex column;
an age-band rate table is kept); `image_pages` have no text layer, so nothing could screen them; `lists_members` says
the file shows people anywhere (any flagged page, or a sheet holding a member table), which logs its downloads and
views like a PHI kind's (E99). Claude's reads leave the flagged pages out only while `AI_MEMBER_DATA_SCREEN` is on
(`pages_left_out`); off, the default, files are read whole as the old app reads them since D-225 (OQ22).

The rules are the old docscan/phi_screen.py's (RULES_VERSION 2), ported: they answer by pattern names, never by text.
Nothing here returns, logs or raises a page's words. Pure, apart from the setting `pages_left_out` reads.
"""

import re

from django.conf import settings

from deals import clock

from . import kinds, pages

VERSION = 2  # bumped whenever a rule changes what is flagged

SSN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
DOB_LABEL = re.compile(r'\b(?:dob|d\.o\.b\.?|date\s+of\s+birth|birth\s*date)\b', re.I)
FULL_DATE = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')
MEMBER_HEADER = re.compile(r'\b(?:employee|member|subscriber|dependent|enrollee)\s+name\b', re.I)
FIRST_NAME = re.compile(r'\bfirst\s+name\b', re.I)
LAST_NAME = re.compile(r'\blast\s+name\b', re.I)
PERSON_WORD = re.compile(
    r'\b(?:name|names|employee|employees|member|members|subscriber|subscribers|enrollee|enrollees|dependent'
    r'|dependents|insured|participant|participants|claimant|claimants)\b',
    re.I,
)
# 'age' as a column heading, never plan wording like 'to age 26'.
DEMOGRAPHIC_WORD = re.compile(
    r'(?<!to )(?<!through )(?<!until )\b(?:age(?!\s*(?:\d|limit))|ages|gender|sex|relationship|zip|zip code|salary'
    r'|hire date|dob|birth)\b',
    re.I,
)
# Not 'claimant' alone: a stop-loss quote prices a deductible 'per claimant'.
CLAIMS_DETAIL = re.compile(r'\b(?:diagnosis|diagnoses|icd)\b', re.I)
SEX_TOKEN = re.compile(r'(?<![\w$.])[MF](?![\w.])')
CAPS_WORD = re.compile(r'\b[A-Z]{3,}\b')
BARE_TWO_DIGITS = re.compile(r'(?<![\d.$,])\b\d{2}\b(?![\d.,%])')
CENTS = re.compile(r'\d\.\d{2}\b')
ZIP5 = re.compile(r'(?<![\d$.,-])\b\d{5}\b(?![\d.,%-])')
MIN_SCREENABLE_TEXT = 25  # fewer extractable characters: an image page, which could hold anything
ROWS_MIN_AGES, ROWS_MIN_ZIPS, ROWS_MIN_SEX = 6, 2, 3


def _birth_dates(text):
    """Full dates whose year is old enough to be a birth date rather than a plan year or an effective date."""
    cutoff = clock.today().year - 16
    return [m for m in FULL_DATE.finditer(text) if int(m.group(3)) <= cutoff]


def phi_flags(text):
    """Why `text` may hold member data, as pattern names, never the text."""
    flags = []
    if SSN.search(text):
        flags.append('ssn')
    if DOB_LABEL.search(text):
        flags.append('dob_label')
    if len(_birth_dates(text)) >= 3:
        flags.append('birth_dates')
    if MEMBER_HEADER.search(text) or (FIRST_NAME.search(text) and LAST_NAME.search(text)):
        flags.append('member_list')
    return flags


def table_flags(text):
    """`phi_flags` plus the shapes of a member table, for a whole page or sheet."""
    flags = phi_flags(text)
    if CLAIMS_DETAIL.search(text):
        flags.append('claims_detail')
    if PERSON_WORD.search(text) and DEMOGRAPHIC_WORD.search(text):
        flags.append('member_table')
    if len(SEX_TOKEN.findall(text)) >= 5:
        flags.append('sex_column')
    return flags


def rows_of_people(text):
    """An age column, more than one ZIP code, or a sex column: rows of people under a member table's heading."""
    return (
        len(BARE_TWO_DIGITS.findall(text)) >= ROWS_MIN_AGES
        or len(set(ZIP5.findall(text))) >= ROWS_MIN_ZIPS
        or len(SEX_TOKEN.findall(text)) >= ROWS_MIN_SEX
    )


def pdf_page_flags(text):
    """`table_flags` plus names flattened into long lines and a page with no text layer. A member table that is a
    page's only reason needs rows of people: alone, the pair is plan wording or an age-band rate page's heading."""
    flags = table_flags(text)
    names_flattened = len(CAPS_WORD.findall(text)) >= 20 and len(BARE_TWO_DIGITS.findall(text)) >= 10
    if names_flattened and len(CENTS.findall(text)) <= 2:
        flags.append('caps_names')
    if flags == ['member_table'] and not rows_of_people(text):
        flags = []
    if len(text.strip()) < MIN_SCREENABLE_TEXT:
        flags.append('no_text')
    return flags


def _result(left_out=(), image=(), lists_members=False):
    return {
        'version': VERSION,
        'left_out_pages': sorted(left_out),
        'image_pages': sorted(image),
        'lists_members': bool(lists_members),
    }


def screen_pdf(raw):
    left_out, image = [], []
    for number, text in enumerate(pages.page_texts(raw), start=1):
        flags = pdf_page_flags(text)
        if 'no_text' in flags:
            image.append(number)
        if any(flag != 'no_text' for flag in flags):
            left_out.append(number)
    return _result(left_out, image, bool(left_out))


def screen_sheets(filename, raw):
    from .sheets import SheetError, load_sheets

    try:
        sheets = load_sheets(filename, raw)
    except SheetError:
        return _result()
    lists = any(table_flags('\n'.join(' '.join(row) for row in sheet['rows'])) for sheet in sheets)
    return _result(lists_members=lists)


def screen(filename, raw, kind):
    """The screen for an uploaded file. An issued proposal is never screened ({}); an image is one image page; a
    file no viewer reads (.docx, .eml) is stored as screened, with nothing found."""
    if kind == 'proposal':
        return {}
    shape = kinds.shape_of(filename)
    if shape == kinds.PDF:
        return screen_pdf(raw)
    if shape == kinds.SHEET:
        return screen_sheets(filename, raw)
    if shape == kinds.IMAGE:
        return _result(image=[1])
    return _result()


def lists_members(document):
    return bool((document.screen or {}).get('lists_members'))


def pages_left_out(document):
    """The pages a Claude read leaves out: the flagged pages while AI_MEMBER_DATA_SCREEN is on, else none (OQ22)."""
    if not getattr(settings, 'AI_MEMBER_DATA_SCREEN', False):
        return []
    return list((document.screen or {}).get('left_out_pages') or [])
