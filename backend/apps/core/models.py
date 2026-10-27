from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantScopedModel(TimeStampedModel):
    """Base class for every model whose rows belong to a single institute.

    Feature apps (students, attendance, fees, ...) inherit from this so that
    tenant isolation works the same way everywhere.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
    )

    objects = TenantScopedQuerySet.as_manager()

    class Meta:
        abstract = True
