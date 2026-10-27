from django.contrib.auth.backends import ModelBackend

from .models import User


class TenantModelBackend(ModelBackend):
    """Authenticate a user inside one institute, or a platform super admin.

    ``tenant=None`` means a platform login (super admins only). The login value
    may be the username or the email address.
    """

    def authenticate(self, request, username=None, password=None, tenant=None, **kwargs):
        if not username or password is None:
            return None
        users = User.objects.filter(tenant=tenant)
        field = "email__iexact" if "@" in username else "username"
        user = users.filter(**{field: username}).first()
        if user is None:
            # Run the hasher anyway so response time does not reveal which usernames exist.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
