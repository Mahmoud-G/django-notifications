from django.contrib import admin


class AbstractNotificationAdmin(admin.ModelAdmin):
    raw_id_fields = ('recipient',)
    list_display = ('recipient', 'actor', 'level', 'target', 'unread', 'public')
    list_filter = ('level', 'unread', 'public', 'timestamp',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "recipient",
            "actor_content_type",
            "target_content_type",
            "action_object_content_type",
        ).prefetch_related("actor", "action_object", "target")
