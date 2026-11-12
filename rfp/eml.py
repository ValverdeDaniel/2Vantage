"""One email draft as an `.eml` file (plan.md §9.11; K63; OQ82: the app sends nothing). Never stored.

An RFC 5322 message with `X-Unsent: 1`, which Outlook desktop opens as an unsent draft with To, CC, the subject and
the attachments filled in; no From header, so Outlook sends from the account that opens it — the rep's own (old
`rfp_email.build_eml`, 891f1b3). `multipart/mixed`: a UTF-8 `text/plain` body (the draft's text and nothing else,
D-143) and the attachments, each typed from the explicit map in `deals.downloads` (bug 39: the slim image's
`mimetypes` has no .xlsx). Built through `members`, so a file that cannot be built refuses the whole draft by its
label (K63, bug 9), never dropping it silently.
"""

from email import policy
from email.message import EmailMessage

from deals.downloads import content_type_for

UNSENT = 'X-Unsent'


def build(draft, found):
    """The message's bytes: `draft` from `drafts.drafts`, `found` the [members.Member] it carries."""
    message = EmailMessage(policy=policy.SMTP)
    if draft.get('to'):
        message['To'] = draft['to']
    if draft.get('cc'):
        message['Cc'] = draft['cc']
    message['Subject'] = draft['subject']
    message[UNSENT] = '1'
    message.set_content(draft['body'], charset='utf-8')
    for member in found:
        maintype, _, subtype = content_type_for(member.name).partition('/')
        message.add_attachment(member.data, maintype=maintype, subtype=subtype, filename=member.name)
    return message.as_bytes()


def filename(ctx, draft):
    return f'{ctx.deal.client.name} - RFP email - {draft["name"]}.eml'
