''' Django notifications settings file '''
# -*- coding: utf-8 -*-
from functools import lru_cache

from django.conf import settings
from django.test.signals import setting_changed


CONFIG_DEFAULTS = {
    'PAGINATE_BY': 20,
    'USE_JSONFIELD': False,
    'SOFT_DELETE': False,
    'NUM_TO_FETCH': 10,
    'CACHE_TIMEOUT': 2,
}


@lru_cache(maxsize=1)
def get_config():
    """
    Return the merged notifications config dict.

    Result is cached after the first call.  The cache is automatically
    invalidated whenever ``DJANGO_NOTIFICATIONS_CONFIG`` (or ``DATABASES``,
    which implies a full settings reload) is changed via ``override_settings``
    in tests.
    """
    user_config = getattr(settings, 'DJANGO_NOTIFICATIONS_CONFIG', {})
    config = CONFIG_DEFAULTS.copy()
    config.update(user_config)
    return config


def _invalidate_config_cache(*, setting, **kwargs):
    """Clear the lru_cache when relevant settings change (test isolation)."""
    if setting in {'DJANGO_NOTIFICATIONS_CONFIG', 'DATABASES'}:
        get_config.cache_clear()


setting_changed.connect(_invalidate_config_cache)
