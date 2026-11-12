"""The Q.3 contracts for accounts: GETs that write nothing and the permission matrix (plan.md §12.3)."""

from conftest import check_permissions, sweep_gets

SAMPLES = {'api/auth/csrf/': {'expect': 204}}
# A wrong password, so no actor's session changes (a sign-in would cycle the session key inside the rolled-back
# savepoint and sign the client out). Logout comes last: it ends the session of each actor that runs it.
SIGN_IN = {'username': 'nobody', 'password': 'wrong'}

MATRIX = [
    ('GET', 'api/auth/csrf/', {'signed_out': 204, 'producer': 204, 'admin': 204}),
    ('POST', 'api/auth/login/', {'signed_out': 400, 'producer': 400, 'admin': 400}, SIGN_IN),
    ('GET', 'api/auth/me/', {'signed_out': 401, 'producer': 200, 'admin': 200}),
    ('POST', 'api/auth/logout/', {'signed_out': 401, 'producer': 204, 'admin': 204}),
]


def test_Q3_accounts_gets_write_nothing(admin_api):
    sweep_gets(admin_api, ('accounts',), SAMPLES)


def test_Q3_accounts_permission_matrix(actors, no_csrf_api):
    check_permissions(actors, ('accounts',), MATRIX, SAMPLES, no_csrf_api)
