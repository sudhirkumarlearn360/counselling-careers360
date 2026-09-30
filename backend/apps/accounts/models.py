from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    OPS_LEAD = "ops_lead", "Ops lead"
    RECEPTION = "reception", "Front desk"
    COUNSELLOR = "counsellor", "Counsellor"


def normalise_email(email: str) -> str:
    """Sign-in email is case- and space-insensitive (CQ-1)."""
    return (email or "").strip().lower()


class StaffUserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email=normalise_email(username))

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=normalise_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.OPS_LEAD)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class StaffUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=12, choices=Role.choices)
    centre = models.ForeignKey(
        "centres.Centre", null=True, blank=True, on_delete=models.PROTECT, related_name="staff"
    )  # reception's centre
    counsellor = models.OneToOneField(
        "counsellors.Counsellor", null=True, blank=True, on_delete=models.PROTECT, related_name="user"
    )
    title = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access only
    date_joined = models.DateTimeField(default=timezone.now)

    objects = StaffUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(role="counsellor") | models.Q(counsellor__isnull=False),
                name="staffuser_counsellor_has_counsellor",
            ),
            models.CheckConstraint(
                check=~models.Q(role="reception") | models.Q(centre__isnull=False),
                name="staffuser_reception_has_centre",
            ),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = normalise_email(self.email)
        super().save(*args, **kwargs)


class LoginAttempt(models.Model):
    """Consecutive failed sign-ins per (normalised) email, reset on success (CQ-2).

    Keyed by email rather than user so unknown emails behave identically.
    """

    email = models.CharField(max_length=254, unique=True)
    failed_count = models.PositiveIntegerField(default=0)
    last_failed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.email}: {self.failed_count}"
