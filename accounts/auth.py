from rest_framework.authentication import SessionAuthentication


class SessionAuth(SessionAuthentication):
    """Django sessions with CSRF on writes. Naming a scheme makes DRF answer 401, not 403, when signed out (§3.6)."""

    def authenticate_header(self, request):
        return 'Session'
