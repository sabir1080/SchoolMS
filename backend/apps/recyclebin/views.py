import datetime
import math

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstituteAdmin
from apps.subscriptions.gating import ActiveSubscription

from .models import KEEP_DAYS, DeletedItem
from .services import RestoreConflict, purge_old, restore


class DeletedItemSerializer(serializers.ModelSerializer):
    deleted_by_name = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()

    class Meta:
        model = DeletedItem
        fields = ["id", "kind", "label", "created_at", "deleted_by_name", "days_left", "restored_at"]

    def get_deleted_by_name(self, item):
        user = item.deleted_by
        return (user.get_full_name() or user.username) if user else None

    def get_days_left(self, item):
        # Whole days, rounded up: an item deleted a minute ago has 30 days left, not 29.
        remaining = (item.created_at + datetime.timedelta(days=KEEP_DAYS) - timezone.now()).total_seconds()
        return max(math.ceil(remaining / 86400), 0)


class RecycleBinView(APIView):
    """What admins deleted in the last 30 days."""

    permission_classes = [IsInstituteAdmin, ActiveSubscription]

    def get(self, request):
        purge_old(request.user.tenant)
        items = DeletedItem.objects.filter(tenant=request.user.tenant, restored_at__isnull=True).select_related("deleted_by")
        return Response(DeletedItemSerializer(items, many=True).data)


class RecycleBinItemView(APIView):
    permission_classes = [IsInstituteAdmin, ActiveSubscription]

    def item(self, request, pk):
        item = DeletedItem.objects.filter(tenant=request.user.tenant, pk=pk, restored_at__isnull=True).first()
        if item is None:
            raise NotFound("This item is not in the recycle bin.")
        return item

    def post(self, request, pk):
        """Restore."""
        try:
            item = restore(self.item(request, pk), request.user)
        except RestoreConflict as exc:
            raise ValidationError(str(exc))
        return Response(DeletedItemSerializer(item).data)

    def delete(self, request, pk):
        """Delete forever."""
        self.item(request, pk).delete()
        return Response(status=204)
