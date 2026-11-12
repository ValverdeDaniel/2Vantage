"""Issue's vocabularies (plan.md §4.6 "Proposal issue states", §7.12; J96, J103): Python constants, served by
/api/meta/ as `proposal.issue` (rule 1), so the packet card holds no list of its own."""

from ..models import ProposalIssue

# An issue's stored files, in the packet card's order, which is the zip's (the old proposal_packet.MEMBERS and
# ProposalPacketCard's ZIP_ROWS at 891f1b3): key, label, the card's hint.
FILES = (
    ('pdf', 'Client PDF', 'The client proposal'),
    ('pptx', 'PowerPoint', 'A 16:9 deck to present from'),
    ('xlsx', 'Client spreadsheet', 'Live tabs for the client'),
)
FILE_KEYS = tuple(key for key, _label, _hint in FILES)
LABELS = {key: label for key, label, _hint in FILES}
EXTENSIONS = {'pdf': 'pdf', 'pptx': 'pptx', 'xlsx': 'xlsx'}
LETTER = 'letter'  # the issue's PDF on US Letter, made from its stored bytes on each download (§9.7)
STATE_LABELS = dict(ProposalIssue.STATES)


def meta():
    return {
        'states': [{'key': key, 'label': label} for key, label in ProposalIssue.STATES],
        'files': [{'key': key, 'label': label, 'hint': hint} for key, label, hint in FILES],
    }
