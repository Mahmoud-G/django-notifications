from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "recipient",
        "actor",
        "verb",
        "unread",
        "timestamp",
    )

    list_filter = (
        "unread",
        "timestamp",
    )

    search_fields = (
        "verb",
        "description",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # select_related covers the recipient FK and the three content-type FKs
        # (avoids one query per row for those).  prefetch_related('actor') then
        # fetches all actor objects in a single query per content-type group.
        return qs.select_related(
            "recipient",
            "actor_content_type",
            "target_content_type",
            "action_object_content_type",
        ).prefetch_related("actor", "action_object", "target")
