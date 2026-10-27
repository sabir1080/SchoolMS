from rest_framework import serializers


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """A related-object field that only accepts objects of the requesting user's institute.

    Pass the unfiltered queryset; it is narrowed to ``request.user.tenant`` here, so an
    id from another institute is rejected as "does not exist".
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        tenant = getattr(getattr(request, "user", None), "tenant", None)
        return queryset.filter(tenant=tenant) if tenant is not None else queryset.none()
