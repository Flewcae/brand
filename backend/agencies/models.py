import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Email-based custom user. Set as AUTH_USER_MODEL from the first migration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Agency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "agencies"

    def __str__(self):
        return self.name


class AgencyMembership(models.Model):
    """Membership table exists from day one even though every member currently
    has the same effective permissions, so a future client-facing or granular
    role can be added without a schema rewrite."""

    class Role(models.TextChoices):
        MEMBER = "member", "Member"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agency_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agency", "user"], name="unique_agency_user"),
        ]
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.agency}"
