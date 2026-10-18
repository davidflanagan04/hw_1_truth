# =============================================================================
# robot-models.py
#
# LLM used: Claude (Sonnet 5.5, Anthropic)
#
# Prompt given to the LLM:
#   "Write a Django models.py for an app called AttendanceChimp. Tables:
#    InstructorProfile and StudentProfile (each one-to-one with Django's User,
#    instead of a single Users table); Course (name, instructor, meeting
#    schedule); Enrollment (many-to-many link between students and courses);
#    Lecture (belongs to a course, has a date and a QR identifier);
#    QRCodeUpload (belongs to a student and optionally a lecture). Include
#    docstrings, __str__ methods, and helper functions is_instructor,
#    is_student and getUploadsForCourse. Prefer a structured meeting schedule
#    (days and times) over free text."
#
# Note: this file is for comparison only. The hyphen in the filename makes it
# non-importable, so Django never loads it.
# =============================================================================

import secrets

from django.contrib.auth.models import User
from django.db import models


def make_qr_identifier():
    """Return a URL-safe random token to encode in a lecture's QR code."""
    return secrets.token_urlsafe(16)


class InstructorProfile(models.Model):
    """Instructor details, linked one-to-one to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="instructor")
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StudentProfile(models.Model):
    """Student details, linked one-to-one to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="student")
    student_id = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_id})"


class Course(models.Model):
    """A course taught by one instructor, with a structured weekly schedule."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"

    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.PROTECT,
                                   related_name="courses")
    meeting_days = models.CharField(
        max_length=20, blank=True,
        help_text="Comma-separated Weekday values, e.g. '1,3' for Tue/Thu.")
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    students = models.ManyToManyField(StudentProfile, through="Enrollment",
                                      related_name="courses")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def meeting_schedule(self):
        """Human-readable schedule such as 'Tuesday, Thursday 10:30-11:50'."""
        days = [self.Weekday(int(d)).label
                for d in self.meeting_days.split(",") if d.strip()]
        if not days:
            return "TBA"
        times = ""
        if self.start_time and self.end_time:
            times = f" {self.start_time:%H:%M}-{self.end_time:%H:%M}"
        return ", ".join(days) + times


class Enrollment(models.Model):
    """Link table: one student enrolled in one course."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "course")]

    def __str__(self):
        return f"{self.student} -> {self.course}"


class Lecture(models.Model):
    """A single class meeting, identified in QR codes by qr_identifier."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE,
                               related_name="lectures")
    date = models.DateField()
    qr_identifier = models.CharField(max_length=64, unique=True,
                                     default=make_qr_identifier)

    class Meta:
        ordering = ["-date"]
        unique_together = [("course", "date")]

    def __str__(self):
        return f"{self.course.name} - {self.date}"


class QRCodeUpload(models.Model):
    """A student's submitted QR code; lecture may be unset if unmatched."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                related_name="uploads")
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="uploads")
    image = models.ImageField(upload_to="qr_uploads/", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} @ {self.uploaded_at:%Y-%m-%d %H:%M}"


def is_instructor(user):
    """True if the user has an InstructorProfile."""
    return hasattr(user, "instructor")


def is_student(user):
    """True if the user has a StudentProfile."""
    return hasattr(user, "student")


def getUploadsForCourse(course):
    """All QRCodeUploads tied to any lecture of the given course."""
    return QRCodeUpload.objects.filter(lecture__course=course)