from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role


class HasRole(BasePermission):
    """Allow access only to users whose role is in ``allowed_roles``.

    Use ``HasRole.for_roles(Role.ADMIN, Role.TEACHER)`` in ``permission_classes``.
    """

    allowed_roles = ()

    @classmethod
    def for_roles(cls, *roles):
        return type(f"HasRole_{'_'.join(roles)}", (cls,), {"allowed_roles": roles})

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


IsSuperAdmin = HasRole.for_roles(Role.SUPER_ADMIN)
IsInstituteAdmin = HasRole.for_roles(Role.ADMIN)


class AdminWriteStaffRead(BasePermission):
    """Institute admins can do everything; teachers can only read."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.role in (Role.ADMIN, Role.TEACHER)
        return user.role == Role.ADMIN
