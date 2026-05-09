from notifications.utils import id2slug
from notifications.settings import get_config

_GFK_SELECT_RELATED = (
    'actor_content_type',
    'target_content_type',
    'action_object_content_type',
)


def get_object_url(instance, notification, request):
    """
    Return the URL for *instance* in the context of a notification.
    Calls ``instance.get_url_for_notifications(notification, request)`` when
    defined, falls back to ``get_absolute_url()``.
    """
    if hasattr(instance, 'get_url_for_notifications'):
        return instance.get_url_for_notifications(notification, request)
    if hasattr(instance, 'get_absolute_url'):
        return instance.get_absolute_url()
    return None


def get_num_to_fetch(request):
    default = get_config()['NUM_TO_FETCH']
    try:
        num = int(request.GET.get('max', default))
        return num if 1 <= num <= 100 else default
    except (ValueError, TypeError):
        return default


def get_notification_list(request, method_name='all', queryset=None):
    """
    Serialize up to ``NUM_TO_FETCH`` notifications into a list of dicts.

    *queryset* — pass a pre-evaluated base queryset (e.g. already filtered and
    counted by the caller) to avoid rebuilding it internally.  When omitted the
    method named *method_name* on ``request.user.notifications`` is used.
    """
    num_to_fetch = get_num_to_fetch(request)

    if queryset is None:
        queryset = getattr(request.user.notifications, method_name)()

    # Apply GFK prefetching once, then slice — avoids N+1 per row.
    queryset = (
        queryset
        .select_related(*_GFK_SELECT_RELATED)
        .prefetch_related('actor', 'target', 'action_object')
    )

    mark_as_read_flag = request.GET.get('mark_as_read')
    notification_list = []
    ids_to_mark = []

    for notification in queryset[:num_to_fetch]:
        # Build a lean dict instead of model_to_dict (avoids forms machinery
        # and keeps only fields the API actually exposes).
        struct = {
            'id':          notification.pk,
            'slug':        id2slug(notification.pk),
            'level':       notification.level,
            'unread':      notification.unread,
            'verb':        notification.verb,
            'description': notification.description,
            'timestamp':   notification.timestamp,
            'public':      notification.public,
            'deleted':     notification.deleted,
            'emailed':     notification.emailed,
        }

        if notification.actor:
            struct['actor'] = str(notification.actor)
            actor_url = get_object_url(notification.actor, notification, request)
            if actor_url:
                struct['actor_url'] = actor_url

        if notification.target:
            struct['target'] = str(notification.target)
            target_url = get_object_url(notification.target, notification, request)
            if target_url:
                struct['target_url'] = target_url

        if notification.action_object:
            struct['action_object'] = str(notification.action_object)
            action_object_url = get_object_url(
                notification.action_object, notification, request
            )
            if action_object_url:
                struct['action_object_url'] = action_object_url

        if notification.data:
            struct['data'] = notification.data

        notification_list.append(struct)

        if mark_as_read_flag and notification.unread:
            ids_to_mark.append(notification.pk)

    # Single bulk UPDATE instead of one save() per notification.
    if ids_to_mark:
        request.user.notifications.filter(pk__in=ids_to_mark).update(unread=False)

    return notification_list
