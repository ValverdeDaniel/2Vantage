"""Review's rows (plan.md §6.12; L.6): a request, the link each person holds, notes, and the last look.

The asks live once on the `ClientRequest`; each person asked gets a `ClientLink` holding who they are, how the link
is protected and what it has done (sent, opened, saved, submitted). Every state — the request's, the link's, whether
it still opens — is worked out on read by `review.rules`, never stored. Vocabularies (security levels, close
reasons, ask scopes) stay out of the migrations (rule 1): `review.rules` and `review.words` hold them and the
services check them.

A link's token is never stored (L.6, plan.md §3.8): the row keeps a random `seed` and the token's SHA-256
(`token_hash`); `review.tokens` signs the seed with the server's key to give the token back for Copy link, and the
portal (slice 54) finds a link by the hash of the token it is given. A PIN is stored only as a hash.

Client answers do not live here: they wait on the owners' rows (`Intake.client`, `Member.client`, …) until a person
approves them (O.3.1).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from census.models import Member
from deals.models import Contact, Deal

USER = settings.AUTH_USER_MODEL


class ClientRequest(models.Model):
    """One ask of the client, to one or more people (L55). `asks` has the shape of plan.md §6.12; every change to it
    bumps `form_version` (L59, slice 57). Closing it (`closed_at`, `close_reason`) ends every link on it (L70)."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='client_requests')
    asks = models.JSONField(default=dict, blank=True)
    message = models.TextField(blank=True)  # ≤ 1,000, checked by the service
    form_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    close_reason = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['deal', 'closed_at'])]

    def __str__(self):
        return f'Request {self.id} on deal {self.deal_id}'


class ClientLink(models.Model):
    """One person's link on a request (L55–L64). `name` and `email` are snapshots of who it went to (a contact's, or
    typed); `contact` stays only while that contact exists (Ch. 20). The life rules are `review.rules.policy`."""

    request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name='links')
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 of the token; the token is never stored
    seed = models.CharField(max_length=32)  # random: the token is this signed with the server's key (tokens.py)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    name = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=254, blank=True)
    security = models.CharField(max_length=10, default='link')  # rules.policy.LEVELS: link or pin
    pin_hash = models.CharField(max_length=128, blank=True)
    pin_tries = models.PositiveSmallIntegerField(default=0)  # wrong tries since the PIN was made; 5 lock it
    pin_version = models.PositiveIntegerField(default=0)  # every new PIN bumps it, ending verified sessions
    blank = models.BooleanField(default=False)  # shows only what they answer, never what else we hold (L66)
    slides = models.BooleanField(default=True)  # a save pushes the expiry out, until a person picks a date (L61)
    expires_at = models.DateTimeField()
    ceiling_at = models.DateTimeField()  # creation plus 30 days: no extension goes past it (L62, OQ81)
    nudge = models.JSONField(default=dict, blank=True)  # {on, by, at, done_at, done_by} (L69; O.2, I.6)
    sent_at = models.DateTimeField(null=True, blank=True)  # copying the link is the send (L71, OQ82)
    opened_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    open_count = models.PositiveIntegerField(default=0)
    first_submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    attested_form_version = models.PositiveIntegerField(null=True, blank=True)
    last_saved_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Link {self.id} on request {self.request_id}'  # never a name or the token


ASK_KINDS = ('ask', 'sendback')


class ReviewNote(models.Model):
    """A note, an ask or send-back in the tray, a client's question, or a reply (L22, L49–L53; slice 56 writes them).

    `key` names the slot: an intake key, a census column, `<form>:<slot>`, a form key, a document slot or
    `census_file`. `member` is RESTRICT, not CASCADE: a census person is only ever soft-removed (Ch. 12), so a note
    keeps its person, and a deal's own delete still takes both. One open ask or send-back draft per (deal, surface,
    key, member), nulls not distinct (B7)."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='review_notes')
    surface = models.CharField(max_length=20)  # intake, census, questionnaire or documents
    key = models.CharField(max_length=120, blank=True)
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.RESTRICT, related_name='+')
    request = models.ForeignKey(ClientRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='notes')
    link = models.ForeignKey(ClientLink, null=True, blank=True, on_delete=models.SET_NULL, related_name='notes')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    audience = models.CharField(max_length=10, default='client')  # client, or team (🔒 Team only)
    kind = models.CharField(max_length=10)  # note, sendback, ask, question or reply
    text = models.TextField(blank=True)  # ≤ 1,000, checked by the service
    author = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')  # null: client
    at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)  # null while a draft waits in the tray
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['at', 'id']
        indexes = [models.Index(fields=['deal', 'resolved_at'])]
        constraints = [
            models.UniqueConstraint(
                fields=['deal', 'surface', 'key', 'member'],
                condition=Q(kind__in=ASK_KINDS, sent_at__isnull=True, resolved_at__isnull=True),
                nulls_distinct=False,
                name='review_note_one_open_draft',
            )
        ]

    def __str__(self):
        return f'{self.kind} {self.id} on deal {self.deal_id}'  # never the text


class Seen(models.Model):
    """The last look at a deal's review, by a person or through a link (L33, L44). It only moves forward."""

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='+')
    user = models.ForeignKey(USER, null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    link = models.ForeignKey(ClientLink, null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    seen_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(user__isnull=False, link__isnull=True) | Q(user__isnull=True, link__isnull=False),
                name='review_seen_user_or_link',
            ),
            models.UniqueConstraint(fields=['deal', 'user'], condition=Q(user__isnull=False), name='review_seen_user'),
            models.UniqueConstraint(fields=['deal', 'link'], condition=Q(link__isnull=False), name='review_seen_link'),
        ]

    def __str__(self):
        return f'Seen on deal {self.deal_id}'
