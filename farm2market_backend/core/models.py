import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating 'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        help_text=_('Date and time when the record was created.')
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('Date and time when the record was last updated.')
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """
    Custom QuerySet for soft delete functionality.
    """
    def delete(self):
        """Soft delete all objects in the queryset."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently delete all objects in the queryset."""
        return super().delete()

    def alive(self):
        """Return only non-deleted objects."""
        return self.filter(is_deleted=False)

    def dead(self):
        """Return only deleted objects."""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """
    Custom manager for soft delete functionality.
    """
    def get_queryset(self):
        """Return only non-deleted objects by default."""
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def all_with_deleted(self):
        """Return all objects including deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Return only deleted objects."""
        return SoftDeleteQuerySet(self.model, using=self._db).dead()


class SoftDeleteModel(models.Model):
    """
    Abstract base class that provides soft delete functionality.
    """
    is_deleted = models.BooleanField(
        _('is deleted'),
        default=False,
        help_text=_('Indicates if the record has been soft deleted.')
    )
    deleted_at = models.DateTimeField(
        _('deleted at'),
        null=True,
        blank=True,
        help_text=_('Date and time when the record was soft deleted.')
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access to all objects including deleted

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the object."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class UUIDModel(models.Model):
    """
    Abstract base class that provides UUID primary key.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for the record.')
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, SoftDeleteModel, UUIDModel):
    """
    Abstract base class that combines all common functionality:
    - UUID primary key
    - Timestamps (created_at, updated_at)
    - Soft delete functionality
    """
    
    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} ({self.id})"


class ActiveManager(models.Manager):
    """
    Manager that returns only active (non-deleted, active=True) objects.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.model, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        if hasattr(self.model, 'is_active'):
            queryset = queryset.filter(is_active=True)
        return queryset


class PublishedManager(models.Manager):
    """
    Manager for published content (is_published=True).
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.model, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        if hasattr(self.model, 'is_published'):
            queryset = queryset.filter(is_published=True)
        return queryset


class StatusChoices(models.TextChoices):
    """
    Common status choices for various models.
    """
    ACTIVE = 'active', _('Active')
    INACTIVE = 'inactive', _('Inactive')
    PENDING = 'pending', _('Pending')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    SUSPENDED = 'suspended', _('Suspended')


class PriorityChoices(models.TextChoices):
    """
    Common priority choices.
    """
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    URGENT = 'urgent', _('Urgent')
