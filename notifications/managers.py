'''
NotificationQuerySet now lives in notifications.base.models.
This module is kept for backwards-compatible imports only.
'''
from notifications.base.models import NotificationQuerySet  # noqa

__all__ = ['NotificationQuerySet']
