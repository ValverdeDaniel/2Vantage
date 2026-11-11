from rest_framework.test import APIClient


def test_login_success_sets_a_session(user):
    client = APIClient()
    response = client.post('/api/auth/login/', {'username': 'dana', 'password': 'pw-Example-1'}, format='json')
    assert response.status_code == 200
    assert response.json()['username'] == 'dana'
    assert client.get('/api/auth/me/').status_code == 200


def test_wrong_password_and_inactive_user_get_the_same_answer(user):
    client = APIClient()
    wrong = client.post('/api/auth/login/', {'username': 'dana', 'password': 'nope'}, format='json')
    user.is_active = False
    user.save()
    inactive = client.post('/api/auth/login/', {'username': 'dana', 'password': 'pw-Example-1'}, format='json')
    assert wrong.status_code == inactive.status_code == 400
    assert wrong.json() == inactive.json() == {'non_field_errors': ['Invalid username or password.']}


def test_me_is_401_when_signed_out(anon_api, db):
    assert anon_api.get('/api/auth/me/').status_code == 401


def test_logout_ends_the_session(api):
    assert api.post('/api/auth/logout/').status_code == 204
    assert api.get('/api/auth/me/').status_code == 401


def test_a_write_without_the_csrf_header_is_refused(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.post('/api/clients/', {'name': 'X'}, format='json')
    assert response.status_code == 403


def test_a_write_with_the_csrf_header_succeeds(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    client.get('/api/auth/csrf/')
    token = client.cookies['csrftoken'].value
    response = client.post('/api/clients/', {'name': 'X'}, format='json', HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 201
