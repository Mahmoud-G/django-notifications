# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince as _timesince
from django.utils.translation import gettext_lazy as _

from swapper import load_model

from notifications import settings as notifications_settings
from notifications.signals import notify
from notifications.utils import id2slug


EXTRA_DATA = notifications_settings.get_config()['USE_JSONFIELD']


def is_soft_delete():
    return notifications_settings.get_config()['SOFT_DELETE']


def assert_soft_delete():
    if not is_soft_delete():
        raise ImproperlyConfigured(
            "To use 'deleted' field, please set 'SOFT_DELETE=True' in settings."
        )


class NotificationQuerySet(models.QuerySet):
    """Notification QuerySet"""

    def unsent(self):
        return self.filter(emailed=False)

    def sent(self):
        return self.filter(emailed=True)

    def unread(self, include_deleted=False):
        if is_soft_delete() and not include_deleted:
            return self.filter(unread=True, deleted=False)
        return self.filter(unread=True)

    def read(self, include_deleted=False):
        if is_soft_delete() and not include_deleted:
            return self.filter(unread=False, deleted=False)
        return self.filter(unread=False)

    def mark_all_as_read(self, recipient=None):
        qset = self.unread(True)
        if recipient:
            qset = qset.filter(recipient=recipient)
        return qset.update(unread=False)

    def mark_all_as_unread(self, recipient=None):
        qset = self.read(True)
        if recipient:
            qset = qset.filter(recipient=recipient)
        return qset.update(unread=True)

    def deleted(self):
        assert_soft_delete()
        return self.filter(deleted=True)

    def active(self):
        assert_soft_delete()
        return self.filter(deleted=False)

    def mark_all_as_deleted(self, recipient=None):
        assert_soft_delete()
        qset = self.active()
        if recipient:
            qset = qset.filter(recipient=recipient)
        return qset.update(deleted=True)

    def mark_all_as_active(self, recipient=None):
        assert_soft_delete()
        qset = self.deleted()
        if recipient:
            qset = qset.filter(recipient=recipient)
        return qset.update(deleted=False)

    def unread_count(self, user):
        from django.db.models import Count, Q
        return (
            self.filter(recipient=user)
            .aggregate(c=Count("id", filter=Q(unread=True)))["c"]
        )

    def bulk_notify(self, sender, recipients, verb, **kwargs):
        from django.contrib.contenttypes.models import ContentType
        actor_ct = ContentType.objects.get_for_model(sender)
        notifications = [
            self.model(
                recipient=user,
                actor_content_type=actor_ct,
                actor_object_id=sender.pk,
                verb=verb,
                **kwargs,
            )
            for user in recipients
        ]
        return self.bulk_create(notifications)


class NotificationLevel(models.TextChoices):
    SUCCESS = "success", "Success"
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class AbstractNotification(models.Model):

    level = models.CharField(
        _("level"),
        choices=NotificationLevel.choices,
        default=NotificationLevel.INFO,
        max_length=20,
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient"),
    )

    unread = models.BooleanField(_("unread"), default=True, db_index=True)

    actor_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="notify_actor",
        verbose_name=_("actor content type"),
    )
    actor_object_id = models.CharField(_("actor object id"), max_length=255)
    actor = GenericForeignKey("actor_content_type", "actor_object_id")

    verb = models.CharField(_("verb"), max_length=255)
    description = models.TextField(_("description"), blank=True, null=True)

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="notify_target",
        blank=True,
        null=True,
    )
    target_object_id = models.CharField(max_length=255, blank=True, null=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    action_object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="notify_action_object",
        blank=True,
        null=True,
    )
    action_object_object_id = models.CharField(max_length=255, blank=True, null=True)
    action_object = GenericForeignKey(
        "action_object_content_type", "action_object_object_id"
    )

    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now, db_index=True)

    public = models.BooleanField(_("public"), default=True, db_index=True)
    deleted = models.BooleanField(_("deleted"), default=False, db_index=True)
    emailed = models.BooleanField(_("emailed"), default=False, db_index=True)

    data = models.JSONField(_("data"), blank=True, null=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["recipient", "unread"]),
            models.Index(fields=["recipient", "deleted"]),
        ]
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        ctx = {
            "actor": self.actor,
            "verb": self.verb,
            "action_object": self.action_object,
            "target": self.target,
            "timesince": self.timesince(),
        }

        if self.target:
            if self.action_object:
                return _(
                    "%(actor)s %(verb)s %(action_object)s on %(target)s %(timesince)s ago"
                ) % ctx
            return _("%(actor)s %(verb)s %(target)s %(timesince)s ago") % ctx

        if self.action_object:
            return _("%(actor)s %(verb)s %(action_object)s %(timesince)s ago") % ctx

        return _("%(actor)s %(verb)s %(timesince)s ago") % ctx

    def timesince(self, now=None):
        return _timesince(self.timestamp, now)

    @property
    def slug(self):
        return id2slug(self.id)

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save(update_fields=["unread"])

    def mark_as_unread(self):
        if not self.unread:
            self.unread = True
            self.save(update_fields=["unread"])

    def actor_object_url(self):
        try:
            url = reverse(
                "admin:{0}_{1}_change".format(
                    self.actor_content_type.app_label,
                    self.actor_content_type.model,
                ),
                args=(self.actor_object_id,),
            )
            return format_html("<a href='{url}'>{id}</a>", url=url, id=self.actor_object_id)
        except NoReverseMatch:
            return self.actor_object_id

    def action_object_url(self):
        try:
            url = reverse(
                "admin:{0}_{1}_change".format(
                    self.action_object_content_type.app_label,
                    self.action_object_content_type.model,
                ),
                args=(self.action_object_object_id,),
            )
            return format_html(
                "<a href='{url}'>{id}</a>",
                url=url,
                id=self.action_object_object_id,
            )
        except NoReverseMatch:
            return self.action_object_object_id

    def target_object_url(self):
        try:
            url = reverse(
                "admin:{0}_{1}_change".format(
                    self.target_content_type.app_label,
                    self.target_content_type.model,
                ),
                args=(self.target_object_id,),
            )
            return format_html("<a href='{url}'>{id}</a>", url=url, id=self.target_object_id)
        except NoReverseMatch:
            return self.target_object_id


def notify_handler(verb, **kwargs):
    kwargs.pop("signal", None)

    recipient = kwargs.pop("recipient")
    actor = kwargs.pop("sender")

    optional_objs = [(kwargs.pop(opt, None), opt) for opt in ("target", "action_object")]

    public = bool(kwargs.pop("public", True))
    description = kwargs.pop("description", None)
    timestamp = kwargs.pop("timestamp", timezone.now())
    level = kwargs.pop("level", NotificationLevel.INFO)
    extra_data = kwargs if kwargs and EXTRA_DATA else None

    Notification = load_model("notifications", "Notification")

    if isinstance(recipient, Group):
        recipients = list(recipient.user_set.all())
    elif isinstance(recipient, (list, models.QuerySet)):
        recipients = list(recipient)
    else:
        recipients = [recipient]

    # Resolve ContentTypes once — get_for_model is cached by Django's CT
    # framework, but calling it N times still has Python-level overhead.
    actor_ct = ContentType.objects.get_for_model(actor)
    optional_ct_map = {}
    for obj, opt in optional_objs:
        if obj is not None:
            optional_ct_map[opt] = (ContentType.objects.get_for_model(obj), obj.pk)

    def _build(recipient):
        n = Notification(
            recipient=recipient,
            actor_content_type=actor_ct,
            actor_object_id=actor.pk,
            verb=str(verb),
            public=public,
            description=description,
            timestamp=timestamp,
            level=level,
        )
        for opt, (ct, pk) in optional_ct_map.items():
            setattr(n, f"{opt}_content_type", ct)
            setattr(n, f"{opt}_object_id", pk)
        if extra_data:
            n.data = extra_data
        return n

    if len(recipients) == 1:
        # Single recipient: use save() so post_save signals fire normally.
        n = _build(recipients[0])
        n.save()
        return [n]

    # Multiple recipients: bulk_create for a single INSERT round-trip.
    # Note: post_save signals are NOT fired by bulk_create — this is the
    # correct trade-off for high-volume multi-recipient sends.
    new_notifications = Notification.objects.bulk_create(
        [_build(r) for r in recipients]
    )
    return new_notifications


notify.connect(notify_handler, dispatch_uid="notifications.models.notification")