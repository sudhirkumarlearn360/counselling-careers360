from django.db import models


class Duty(models.TextChoices):
    ON_DESK = "on_desk", "On desk"
    ON_BREAK = "on_break", "On break"
    OFF_DUTY = "off_duty", "Off duty"


class Counsellor(models.Model):
    """A person. Posted to centres through `Posting`."""

    name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=10)
    streams = models.JSONField(default=list)  # >= 1 of Stream values; enforced by services
    expected_session_min = models.PositiveSmallIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_session_min__gte=1), name="counsellor_expected_session_gte_1"
            ),
        ]

    def __str__(self):
        return self.name

    def covers(self, stream: str) -> bool:
        return stream in (self.streams or [])


class Posting(models.Model):
    """The roster: one counsellor at one centre at one desk (CQ-9/11/50)."""

    counsellor = models.ForeignKey(Counsellor, on_delete=models.PROTECT, related_name="postings")
    centre = models.ForeignKey("centres.Centre", on_delete=models.PROTECT, related_name="postings")
    desk_label = models.CharField(max_length=40)
    duty = models.CharField(max_length=10, choices=Duty.choices, default=Duty.OFF_DUTY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["centre_id", "desk_label"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "desk_label"], name="posting_unique_desk_per_centre"),
            models.UniqueConstraint(
                fields=["counsellor", "centre"], name="posting_unique_counsellor_per_centre"
            ),
        ]
        indexes = [models.Index(fields=["centre", "duty"])]

    def __str__(self):
        return f"{self.counsellor} @ {self.centre} {self.desk_label}"
