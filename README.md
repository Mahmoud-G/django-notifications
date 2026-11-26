# `django-notifications` Documentation

> **Forked & upgraded** from [django-notifications-hq](https://github.com/django-notifications/django-notifications) — fully compatible with **Django 4.2, 5.0, 5.1, 5.2+** and **Python 3.9+**. All deprecated APIs removed, migrations modernised, and several performance optimisations applied.

[django-notifications](https://github.com/Mahmoud-G/django-notifications) is a GitHub notification-like app for Django, derived from [django-activity-stream](https://github.com/justquick/django-activity-stream).

The major difference between `django-notifications` and `django-activity-stream`:

- `django-notifications` is for building something like GitHub "Notifications"
- `django-activity-stream` is for building GitHub "News Feed"

Notifications are action events categorised by four main components:

- **Actor** — The object that performed the activity.
- **Verb** — The verb phrase that identifies the action.
- **Action Object** *(Optional)* — The object linked to the action itself.
- **Target** *(Optional)* — The object to which the activity was performed.

`Actor`, `Action Object`, and `Target` are `GenericForeignKeys` to any arbitrary Django object.

**Example:** [justquick](https://github.com/justquick/) *(actor)* **closed** *(verb)* [issue 2](https://github.com/justquick/django-activity-stream/issues/2) *(action\_object)* on [activity-stream](https://github.com/justquick/django-activity-stream/) *(target)* 12 hours ago.

Nomenclature is based on the Activity Streams Spec: <http://activitystrea.ms/specs/atom/1.0/>

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.9, 3.10, 3.11, 3.12, 3.13 |
| Django | 4.2, 5.0, 5.1, 5.2 |
| swapper | any recent version |

No third-party `jsonfield` package required — the built-in `models.JSONField` (Django 3.1+) is used.

---

## Installation

### From GitHub (recommended)

```bash
pip install git+https://github.com/Mahmoud-G/django-notifications.git
```

### In `requirements.txt`

```
git+https://github.com/Mahmoud-G/django-notifications.git
```
### In `requirements.txt` with Docker if git is not installed
```
https://github.com/Mahmoud-G/django-notifications/archive/refs/heads/master.tar.gz
```
### In `pyproject.toml` (PEP 621)

```toml
[project]
dependencies = [
    "django-notifications @ git+https://github.com/Mahmoud-G/django-notifications.git",
]
```

### Pinning to a specific commit (for reproducible builds)

```
git+https://github.com/Mahmoud-G/django-notifications.git@<commit-sha>
```

---

## Setup

### 1. Add to `INSTALLED_APPS`

The app must come after `django.contrib.auth` and any app that will generate notifications:

```python
INSTALLED_APPS = (
    'django.contrib.auth',
    ...
    'notifications',
    ...
)
```

### 2. Add URL configuration

```python
from django.urls import include, path

urlpatterns = [
    ...
    path('inbox/notifications/', include('notifications.urls', namespace='notifications')),
    ...
]
```

### 3. Run migrations

```bash
python manage.py migrate notifications
```

---

## Configuration

Add `DJANGO_NOTIFICATIONS_CONFIG` to your `settings.py`. All keys are optional — the defaults are shown below:

```python
DJANGO_NOTIFICATIONS_CONFIG = {
    'USE_JSONFIELD': False,   # Store arbitrary extra data on notifications
    'SOFT_DELETE':   False,   # Mark as deleted instead of removing from DB
    'NUM_TO_FETCH':  10,      # Default number of notifications returned by live API
    'PAGINATE_BY':   20,      # Notifications per page in list views
    'CACHE_TIMEOUT': 2,       # Seconds to cache unread count in template tags
}
```

---

## Generating Notifications

### Via a signal handler

```python
from django.db.models.signals import post_save
from notifications.signals import notify
from myapp.models import MyModel

def my_handler(sender, instance, created, **kwargs):
    notify.send(instance, recipient=some_user, verb='was saved')

post_save.connect(my_handler, sender=MyModel)
```

### Inline anywhere in your code

```python
from notifications.signals import notify

notify.send(actor, recipient=user, verb='you reached level 10')
```

### Full signature

```python
notify.send(
    actor,
    recipient,          # User, Group, list of Users, or QuerySet of Users
    verb,               # string  (required)
    action_object=obj,  # any model instance (optional)
    target=obj,         # any model instance (optional)
    level='info',       # 'success' | 'info' | 'warning' | 'error'
    description='...',  # string (optional)
    public=True,        # bool (optional)
    timestamp=None,     # datetime (optional, defaults to now)
)
```

> **Multiple recipients:** When `recipient` is a `Group`, a `list`, or a `QuerySet`, a single `bulk_create` call is used — far more efficient than one `save()` per user.

### Extra data

Enable arbitrary JSON data on notifications:

```python
# settings.py
DJANGO_NOTIFICATIONS_CONFIG = {'USE_JSONFIELD': True}
```

Then pass any extra keyword arguments to `notify.send(...)`:

```python
notify.send(actor, recipient=user, verb='liked', extra_key='extra_value')
# notification.data == {'extra_key': 'extra_value'}
```

### Soft delete

By default, `delete/<slug>/` permanently removes the record. To mark it deleted instead:

```python
DJANGO_NOTIFICATIONS_CONFIG = {'SOFT_DELETE': True}
```

With this option, `unread()` and `read()` automatically exclude `deleted=True` records, and the `deleted()`, `active()`, `mark_all_as_deleted()`, and `mark_all_as_active()` queryset methods become available.

---

## API

### QuerySet methods

All methods are available via `Notification.objects` and via the reverse relation `user.notifications`:

```python
user.notifications.unread()      # all unread for this user
Notification.objects.unread()    # all unread globally
```

| Method | Description |
|---|---|
| `qs.unsent()` | Notifications not yet emailed (`emailed=False`) |
| `qs.sent()` | Notifications that have been emailed |
| `qs.unread()` | Unread notifications. Excludes `deleted=True` when `SOFT_DELETE=True` |
| `qs.read()` | Read notifications. Excludes `deleted=True` when `SOFT_DELETE=True` |
| `qs.mark_all_as_read([recipient])` | Mark all unread as read (optionally filtered by recipient) |
| `qs.mark_all_as_unread([recipient])` | Mark all read as unread |
| `qs.deleted()` | `deleted=True` records. Requires `SOFT_DELETE=True` |
| `qs.active()` | `deleted=False` records. Requires `SOFT_DELETE=True` |
| `qs.mark_all_as_deleted([recipient])` | Soft-delete all active. Requires `SOFT_DELETE=True` |
| `qs.mark_all_as_active([recipient])` | Restore all soft-deleted. Requires `SOFT_DELETE=True` |
| `qs.unread_count(user)` | Return the unread count for a specific user (single aggregation query) |
| `qs.bulk_notify(sender, recipients, verb, **kwargs)` | Create notifications for many recipients in one `INSERT` |

### Model methods

#### `obj.timesince([datetime])`

Returns a human-readable time-since string (e.g. `"3 hours"`), wrapping Django's built-in `timesince`.

#### `obj.mark_as_read()`

Mark this notification as read. Issues a targeted `UPDATE` on the `unread` field only.

#### `obj.mark_as_unread()`

Mark this notification as unread.

#### `obj.slug`

Property — returns the URL-safe numeric slug for this notification.

---

## Template Tags

Load the tags at the top of your template:

```html
{% load notifications_tags %}
```

### `notifications_unread`

Returns the number of unread notifications for the current user, or an empty string for anonymous users. The result is cached (see `CACHE_TIMEOUT`).

```html
{% notifications_unread as unread_count %}
{% if unread_count %}
    You have <strong>{{ unread_count }}</strong> unread notifications.
{% endif %}
```

### `has_notification`

Filter — returns `True` if the user has any unread notifications.

```html
{% if request.user|has_notification %}
    <span class="badge">New</span>
{% endif %}
```

---

## Live-Updater API

Two JSON endpoints keep the UI up to date without a page reload.

### `GET /inbox/notifications/api/unread_count/`

```json
{"unread_count": 3}
```

### `GET /inbox/notifications/api/unread_list/`

```json
{
  "unread_count": 3,
  "unread_list": [
    {
      "id": 42,
      "slug": "110951",
      "level": "info",
      "unread": true,
      "verb": "commented on",
      "description": null,
      "timestamp": "2024-06-01T12:00:00Z",
      "public": true,
      "deleted": false,
      "emailed": false,
      "actor": "Alice",
      "actor_url": "/users/alice/",
      "target": "Post #7",
      "target_url": "/posts/7/",
      "data": null
    }
  ]
}
```

**Query parameters:**

| Parameter | Description |
|---|---|
| `max` | Maximum number of notifications to return (1–100, default from `NUM_TO_FETCH`) |
| `mark_as_read` | Any truthy value marks the returned notifications as read in one bulk `UPDATE` |

URLs for `actor`, `target`, and `action_object` are resolved via `Model.get_absolute_url()`. Override just for notifications by implementing `Model.get_url_for_notifications(notification, request)`.

### `GET /inbox/notifications/api/all_count/`

```json
{"all_count": 25}
```

### `GET /inbox/notifications/api/all_list/`

Same shape as `unread_list` but returns all notifications regardless of read status.

---

## Live-Updater JavaScript Widget

Requires the bundled `notify.js` (no external dependencies).

### 1. Load the script and register callbacks

```html
{% load notifications_tags %}

<script src="{% static 'notifications/notify.js' %}" type="text/javascript"></script>
{% register_notify_callbacks callbacks='fill_notification_list,fill_notification_badge' %}
```

`register_notify_callbacks` arguments:

| Argument | Default | Description |
|---|---|---|
| `badge_class` | `live_notify_badge` | CSS class of the element showing the unread count |
| `menu_class` | `live_notify_list` | CSS class of the element that receives the notification list |
| `refresh_period` | `15` | Poll interval in seconds |
| `fetch` | `5` | Number of notifications to fetch per poll |
| `callbacks` | `''` | Comma-separated list of JS functions to call each poll |
| `api_name` | `list` | `'list'` or `'count'` |
| `mark_as_read` | `False` | Mark fetched notifications as read automatically |
| `nonce` | `None` | CSP nonce for the injected `<script>` tag |

### 2. Unread count badge

```html
{% live_notify_badge %}
{# or with a custom class: #}
{% live_notify_badge badge_class="badge badge-pill badge-danger" %}
```

### 3. Notification list

```html
{% live_notify_list %}
{# or with Bootstrap: #}
{% live_notify_list list_class="dropdown-menu" %}
```

### 4. Custom JavaScript callback

```javascript
function my_notification_handler(data) {
    for (var i = 0; i < data.unread_list.length; i++) {
        console.log(data.unread_list[i]);
    }
}
```

```html
{% register_notify_callbacks callbacks='fill_notification_badge,my_notification_handler' %}
```

---

## Custom (Swappable) Notification Model

If you need to add fields or customise behaviour, extend `AbstractNotification`:

```python
# your_app/models.py
from django.db import models
from notifications.base.models import AbstractNotification

class Notification(AbstractNotification):
    category = models.ForeignKey('myapp.Category', on_delete=models.CASCADE)

    class Meta(AbstractNotification.Meta):
        abstract = False
```

```python
# settings.py
NOTIFICATIONS_NOTIFICATION_MODEL = 'your_app.Notification'
```

---

## DRF Serializer Example

```python
from rest_framework import serializers

class GenericNotificationRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        if isinstance(value, Foo):
            return FooSerializer(value).data
        if isinstance(value, Bar):
            return BarSerializer(value).data

class NotificationSerializer(serializers.Serializer):
    recipient = PublicUserSerializer(read_only=True)
    unread    = serializers.BooleanField(read_only=True)
    actor     = GenericNotificationRelatedField(read_only=True)
    target    = GenericNotificationRelatedField(read_only=True)
```

See: <https://www.django-rest-framework.org/api-guide/relations/#generic-relationships>

---

## Notes

### Email Notification

Sending email is not built into this library. Use the `Notification.emailed` field to track which notifications have been emailed, and implement your own email logic using Django's email backend.

### Sample App

A sample app is included at `notifications/tests/sample_notifications` to test extensibility.

```bash
export SAMPLE_APP=1
python manage.py runserver
# unset when done
unset SAMPLE_APP
```

---

## What Changed in This Fork

This fork upgrades the upstream package to be compatible with modern Django (4.2–5.x) and Python (3.9+), with several correctness and performance fixes:

| Area | Change |
|---|---|
| **Django compatibility** | Supports Django 4.2, 5.0, 5.1, 5.2. All removed APIs cleaned up. |
| **`default_app_config`** | Removed (deprecated in Django 3.2, removed in 4.1). |
| **URLs** | `django.conf.urls.url` → `re_path`; `django.core.urlresolvers` removed. |
| **`is_authenticated`** | Removed old callable `try/except TypeError` pattern — now uses the property directly. |
| **`assignment_tag`** | Removed (dropped in Django 2.0). |
| **Migrations** | `index_together` / `AlterIndexTogether` replaced with `AddIndex` (removed in Django 5.2). |
| **`jsonfield` removed** | Third-party `jsonfield` package replaced with `models.JSONField` (built-in since Django 3.1). |
| **`id2slug` / `slug2id`** | Fixed inconsistency: both now use the same numeric-offset encoding. |
| **N+1 queries** | `select_related` + `prefetch_related` on all GFK relationships in list views, API views, and the admin. |
| **`get_notification_list`** | Replaced `model_to_dict` (forms machinery) with a lean hand-built dict; bulk `UPDATE` for mark-as-read. |
| **`notify_handler`** | Resolves ContentTypes once; uses `bulk_create` for multiple recipients (single `INSERT`). |
| **Config caching** | `get_config()` now uses `lru_cache` + `setting_changed` signal for safe cache invalidation in tests. |
| **Per-user cache key** | Template tag cache key now scoped to `user.pk` (was shared across all users). |
| **`live_unread_notification_list`** | `unread_count` is computed after mark-as-read runs, so the count is always accurate. |
| **`unread_count()` / `bulk_notify()`** | New convenience methods added to `NotificationQuerySet`. |
| **`managers.py`** | Orphaned duplicate `NotificationQuerySet` replaced with a re-export from `base.models`. |
| **`setup.py`** | `jsonfield` and `packaging` removed from dependencies; `django>=4.2`, `python_requires>=3.9`. |

---

## Credits

Original package by the [django-notifications](https://github.com/django-notifications/django-notifications) team:

- [Alvaro Leonel](https://github.com/AlvaroLQueiroz)
- [Federico Capoano](https://github.com/nemesisdesign)
- [Samuel Spencer](https://github.com/LegoStormtroopr)
- [Yang Yubo](https://github.com/yangyubo)
- [YPCrumble](https://github.com/YPCrumble)
- [Zhongyuan Zhang](https://github.com/zhang-z)

Django 4.2+ / 5.x upgrade and optimisations by [Mahmoud-G](https://github.com/Mahmoud-G).
