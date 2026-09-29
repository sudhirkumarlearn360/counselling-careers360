from django.apps import apps
from django.db import models, transaction
from django.utils.text import slugify


class CentreStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    LIVE = "live", "Live"
    CLOSED = "closed", "Closed"


class Centre(models.Model):
    """One city + venue + date (the prototype's `event`)."""

    city = models.CharField(max_length=100)
    venue = models.CharField(max_length=200)
    date = models.DateField()
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    expected_students = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=CentreStatus.choices, default=CentreStatus.PLANNED)
    slug = models.SlugField(max_length=80, unique=True)
    front_desk_phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "city"]
        indexes = [models.Index(fields=["date", "status"]), models.Index(fields=["city", "date"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(closes_at__gt=models.F("opens_at")), name="centre_closes_after_opens"
            ),
        ]

    def __str__(self):
        return f"{self.city} {self.date:%Y-%m-%d}"

    def _unique_slug(self) -> str:
        base = slugify(f"{self.city}-{self.date:%Y-%m-%d}")[:70] or "centre"
        slug, n = base, 2
        while Centre.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def save(self, *args, **kwargs):
        adding = self._state.adding
        if not self.slug:
            self.slug = self._unique_slug()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if adding:
                # Every centre has its settings row and its token sequence from birth (CQ-19).
                CentreSettings.objects.get_or_create(centre=self)
                apps.get_model("queue", "TokenSequence").objects.get_or_create(centre=self)


class CentreSettings(models.Model):
    centre = models.OneToOneField(Centre, on_delete=models.CASCADE, related_name="settings")
    target_session_min = models.PositiveSmallIntegerField(default=15)
    wait_sla_min = models.PositiveSmallIntegerField(default=30)
    recall_limit = models.PositiveSmallIntegerField(default=2)
    whatsapp_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "centre settings"

    def __str__(self):
        return f"Settings for {self.centre}"
