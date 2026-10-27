from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class TenantAwareJWTAuthentication(JWTAuthentication):
    """JWT authentication that also locks out users of a suspended institute."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.tenant_id and not user.tenant.is_active:
            raise AuthenticationFailed("This institute account is suspended.", code="tenant_inactive")
        return user
