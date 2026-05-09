# -*- coding: utf-8 -*-
''' Django Notifications example views '''
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.generic import ListView
from swapper import load_model

from notifications import settings as notification_settings
from notifications.helpers import get_notification_list
from notifications.utils import slug2id

Notification = load_model('notifications', 'Notification')


class NotificationViewList(ListView):
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = notification_settings.get_config()['PAGINATE_BY']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


_GFK_SELECT_RELATED = (
    'actor_content_type',
    'target_content_type',
    'action_object_content_type',
)


def _prefetch_notifications(qs):
    """Apply consistent select_related + prefetch_related for GFK fields."""
    return qs.select_related(*_GFK_SELECT_RELATED).prefetch_related(
        'actor', 'target', 'action_object'
    )


class AllNotificationsList(NotificationViewList):
    """
    Index page for authenticated user
    """

    def get_queryset(self):
        if notification_settings.get_config()['SOFT_DELETE']:
            qset = self.request.user.notifications.active()
        else:
            qset = self.request.user.notifications.all()
        return _prefetch_notifications(qset)


class UnreadNotificationsList(NotificationViewList):

    def get_queryset(self):
        return _prefetch_notifications(self.request.user.notifications.unread())


@login_required
def mark_all_as_read(request):
    request.user.notifications.mark_all_as_read()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))
    return redirect('notifications:unread')


@login_required
def mark_as_read(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)
    notification.mark_as_read()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@login_required
def mark_as_unread(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)
    notification.mark_as_unread()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@login_required
def delete(request, slug=None):
    notification_id = slug2id(slug)

    notification = get_object_or_404(
        Notification, recipient=request.user, id=notification_id)

    if notification_settings.get_config()['SOFT_DELETE']:
        notification.deleted = True
        notification.save()
    else:
        notification.delete()

    _next = request.GET.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:all')


@never_cache
def live_unread_notification_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})
    return JsonResponse({
        'unread_count': request.user.notifications.unread().count(),
    })


@never_cache
def live_unread_notification_list(request):
    ''' Return a json with a unread notification list '''
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0, 'unread_list': []})

    # get_notification_list may mark some notifications as read (when
    # ?mark_as_read=1 is present).  Count AFTER the list is built so the
    # returned unread_count reflects any marks that were just applied.
    unread_list = get_notification_list(request, 'unread')
    unread_count = request.user.notifications.unread().count()

    return JsonResponse({
        'unread_count': unread_count,
        'unread_list': unread_list,
    })


@never_cache
def live_all_notification_list(request):
    ''' Return a json with all notifications list '''
    if not request.user.is_authenticated:
        return JsonResponse({'all_count': 0, 'all_list': []})

    all_qs = request.user.notifications.all()
    all_count = all_qs.count()
    all_list = get_notification_list(request, queryset=all_qs)

    return JsonResponse({
        'all_count': all_count,
        'all_list': all_list,
    })


@never_cache
def live_all_notification_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'all_count': 0})
    return JsonResponse({
        'all_count': request.user.notifications.count(),
    })
