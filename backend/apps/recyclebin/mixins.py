from .services import trash


class RecycleBinMixin:
    """Deleting through this viewset keeps a copy in the recycle bin for 30 days."""

    def perform_destroy(self, instance):
        trash(instance, self.request.user)
