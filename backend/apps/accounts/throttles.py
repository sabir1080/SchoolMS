from rest_framework.throttling import SimpleRateThrottle


class LoginAccountThrottle(SimpleRateThrottle):
    """Limits login attempts per account (institute + username) and client IP.

    Stops password guessing on one account without blocking a whole computer lab
    that shares one internet connection.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request, "data") else {}
        account = f"{data.get('institute_code', '')}:{data.get('username', '')}".strip().lower()
        return self.cache_format % {"scope": self.scope, "ident": f"{self.get_ident(request)}:{account}"}


class LoginIPThrottle(SimpleRateThrottle):
    """A looser cap on all logins from one IP address."""

    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
