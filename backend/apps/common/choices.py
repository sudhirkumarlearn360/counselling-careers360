"""Domain enums with the exact values from counselqueue-domain."""

from django.db import models


class Stream(models.TextChoices):
    PCM = "PCM", "Science – PCM"
    PCB = "PCB", "Science – PCB"
    PCMB = "PCMB", "Science – PCMB"
    COM = "COM", "Commerce"
    HUM = "HUM", "Humanities / Arts"
    OTH = "OTH", "Other"


class Exam(models.TextChoices):
    JEE = "JEE", "JEE"
    NEET = "NEET", "NEET"
    CUET = "CUET", "CUET"
    CLAT = "CLAT", "CLAT"
    OTHER = "Other", "Other"
    NONE = "None / not sure", "None / not sure"  # exclusive with the others


class Clarity(models.TextChoices):
    VERY_CLEAR = "Very clear", "Very clear"
    SHORTLISTED = "Have shortlisted options", "Have shortlisted options"
    NEED_HELP = "Need help shortlisting", "Need help shortlisting"
    CONFUSED = "Completely confused", "Completely confused"


class Help(models.TextChoices):
    COLLEGE = "College selection", "College selection"
    COURSE = "Course selection", "Course selection"
    COMPARISON = "College & course comparison", "College & course comparison"
    ADMISSION = "Admission / counselling", "Admission / counselling"
    CUTOFFS = "Cut-offs & college chances", "Cut-offs & college chances"
    EXAMS = "Entrance exams", "Entrance exams"
    OTHER = "Other", "Other"


class Klass(models.TextChoices):
    CLASS_11 = "Class 11", "Class 11"
    CLASS_12 = "Class 12", "Class 12"
    DROPPER = "Dropper / repeat year", "Dropper / repeat year"
    GRADUATE = "Graduate", "Graduate"
    PARENT = "Parent enquiring", "Parent enquiring"


class Outcome(models.TextChoices):
    """null on the model = "Not set" (reported distinctly, CQ-48/61)."""

    READY = "ready", "Ready to apply"
    INTERESTED = "interested", "Interested, needs time"
    EXPLORING = "exploring", "Just exploring"
    NOT_FIT = "not_fit", "Not a fit"


OUTCOME_NOT_SET_LABEL = "Not set"
