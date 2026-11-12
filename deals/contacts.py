"""Contact roles and the one primary-contact rule (plan.md §4.6, §6.2; B13, M30, OQ106). Pure: no database.

The roles are §4.6's seven: the old eighth, `partner_agent`, is not kept, because a split row marks the partner who
works the account (H13, M81). Every role but `prior_broker` is on the client's side. `primary(contacts)` is what RFP,
the questionnaire's officer, review and the Overview read (N.1, O.6 #25).
"""

OWNER = 'owner'
DECISION_MAKER = 'decision_maker'
HR_ADMIN = 'hr_admin'
BENEFIT_ADMIN = 'benefit_admin'
PAYROLL_CONTACT = 'payroll_contact'
BILLING = 'billing'
PRIOR_BROKER = 'prior_broker'

# Served by /api/meta/ as `contact_roles` (rule 1), in the old app's order (891f1b3 CaseContact.ROLE_CHOICES).
ROLES = [
    (OWNER, 'Owner'),
    (DECISION_MAKER, 'Decision Maker'),
    (HR_ADMIN, 'HR Admin'),
    (BENEFIT_ADMIN, 'Benefit Administrator'),
    (PAYROLL_CONTACT, 'Payroll Contact'),
    (BILLING, 'Billing'),
    (PRIOR_BROKER, 'Prior Broker'),
]
LABELS = dict(ROLES)
CLIENT_SIDE = tuple(key for key, _ in ROLES if key != PRIOR_BROKER)
ADMINS = (HR_ADMIN, BENEFIT_ADMIN)  # who intake's readiness and the fallback below look for (B21, M30)

FIELDS = ('role', 'name', 'title', 'email', 'phone', 'is_primary')
LIMITS = {'name': 200, 'title': 200, 'email': 254, 'phone': 50}


def label(role):
    return LABELS.get(role, role)


def primary(contacts):
    """The client's main contact, or None: the one marked primary on a client-side role, else the first HR admin or
    benefit administrator, else the first client-side contact; never a prior broker. `contacts` in their order."""
    client_side = [contact for contact in contacts if contact.role in CLIENT_SIDE]
    return (
        next((contact for contact in client_side if contact.is_primary), None)
        or next((contact for contact in client_side if contact.role in ADMINS), None)
        or next(iter(client_side), None)
    )


def meta():
    """/api/meta/ `contact_roles`: each role, and whether it is on the client's side."""
    return [{'key': key, 'label': text, 'client_side': key in CLIENT_SIDE} for key, text in ROLES]
