"""The Q.3 contracts for accounts: GETs that write nothing and the permission matrix (plan.md §12.3)."""

from conftest import check_permissions, sweep_gets

# Microsoft 365 sign-in is off in tests unless a test turns it on (slice 47), so its two steps answer 404 here and write
# nothing; turned on, they write the session as every sign-in does (test_m365_signin.py).
SAMPLES = {
    'api/auth/csrf/': {'expect': 204},
    'api/auth/microsoft/': {'expect': 404},
    'api/auth/microsoft/callback/': {'expect': 404},
}
# A wrong password, so no actor's session changes (a sign-in would cycle the session key inside the rolled-back
# savepoint and sign the client out). Logout comes last: it ends the session of each actor that runs it.
SIGN_IN = {'username': 'nobody', 'password': 'wrong'}

MATRIX = [
    ('GET', 'api/auth/csrf/', {'signed_out': 204, 'producer': 204, 'admin': 204}),
    ('POST', 'api/auth/login/', {'signed_out': 400, 'producer': 400, 'admin': 400}, SIGN_IN),
    ('GET', 'api/auth/me/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
    ('GET', 'api/auth/options/', {'signed_out': 200, 'producer': 200, 'admin': 200}),
    ('GET', 'api/auth/microsoft/', {'signed_out': 404, 'producer': 404, 'admin': 404}),
    ('GET', 'api/auth/microsoft/callback/', {'signed_out': 404, 'producer': 404, 'admin': 404}),
    ('POST', 'api/auth/logout/', {'signed_out': 401, 'producer': 204, 'admin': 204}),
]


def test_Q3_accounts_gets_write_nothing(admin_api):
    sweep_gets(admin_api, ('accounts',), SAMPLES)


def test_Q3_accounts_permission_matrix(actors, no_csrf_api):
    check_permissions(actors, ('accounts',), MATRIX, SAMPLES, no_csrf_api)
