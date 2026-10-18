"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- InstructorProfile : extends Django User -> instructor-specific data
- StudentProfile    : extends Django User -> student-specific data
- Course            : a course taught by one instructor
- Enrollment        : junction table linking students to courses
- Lecture           : a single class meeting (has a QR-code identifier)
- QRCodeUpload      : a student's uploaded QR-code photograph

Design notes
------------
Separate profile tables instead of one Users table.
    Django's built-in ``User`` already handles authentication (username,
    password hashing, sessions, permissions).  Rather than replacing or
    subclassing it, each role gets its own profile table attached through a
    OneToOneField.  Instructors and students have different attributes
    (``department`` vs. a unique CNetID ``student_id``); a single wide Users
    table would need many nullable columns that only apply to one role, and
    the database could not enforce, e.g., that every student has a
    ``student_id``.  Separate tables keep each one tight and let foreign keys
    point at the right kind of person: ``Course.instructor`` can only
    reference an InstructorProfile, and ``Enrollment.student`` can only
    reference a StudentProfile, so the schema itself rules out a student
    teaching a course or an instructor enrolling in one.  Role checks are the
    helpers ``is_instructor`` and ``is_student``.

Enrollment as an explicit through table.
    The student<->course relation is many-to-many.  Modelling it with an
    explicit ``Enrollment`` model (instead of an invisible auto-generated
    table) lets us add a unique constraint on (student, course) so a student
    cannot be enrolled twice, and leaves room for extra fields later.

Lecture QR identifiers.
    Each lecture gets a unique random uuid4 hex string.  The default is the
    module-level function ``generate_qr_identifier`` (not a lambda) so that
    Django migrations can serialize it.

QRCodeUpload keeps its lecture nullable.
    A student may upload an image whose QR text matches no lecture, and a
    lecture may later be deleted.  The raw ``qr_text`` is always stored, and
    the lecture FK uses SET_NULL so upload history is not lost.
"""

import logging
import uuid

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)  # allows logger.warning(), logger.info(), etc.


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class InstructorProfile(models.Model):
    """Instructor-specific data attached one-to-one to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="instructor_profile")
    department = models.CharField(max_length=100)

    def __str__(self):
        """Return the instructor's username and department."""
        return f"{self.user.username} ({self.department})"


class StudentProfile(models.Model):
    """Student-specific data attached one-to-one to a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="student_profile")
    student_id = models.CharField(max_length=50, unique=True)  # CNetID

    def __str__(self):
        """Return the student's CNetID."""
        return self.student_id


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(models.Model):
    """A course taught by one instructor, with many enrolled students."""

    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE,
                                   related_name="courses")
    meeting_schedule = models.CharField(max_length=200)
    students = models.ManyToManyField(StudentProfile, through="Enrollment",
                                      related_name="courses")

    def __str__(self):
        """Return the course name."""
        return self.name


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    """Junction row linking a student to a course (at most once)."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE,
                               related_name="enrollments")

    class Meta:
        """Prevent duplicate (student, course) enrollments."""

        constraints = [
            models.UniqueConstraint(fields=["student", "course"],
                                    name="unique_student_course"),
        ]

    def __str__(self):
        """Return 'student -> course'."""
        return f"{self.student} -> {self.course}"


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def generate_qr_identifier():
    """Return a random uuid4 hex string (module-level so migrations can serialize it)."""
    return uuid.uuid4().hex


class Lecture(models.Model):
    """A single class meeting, identified by a unique random QR identifier."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE,
                               related_name="lectures")
    date = models.DateField()
    qr_identifier = models.CharField(max_length=32, unique=True,
                                     default=generate_qr_identifier)

    def __str__(self):
        """Return the course name and lecture date."""
        return f"{self.course} on {self.date}"


# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------

class QRCodeUpload(models.Model):
    """A student's uploaded QR code, optionally matched to a lecture."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                related_name="uploads")
    lecture = models.ForeignKey(Lecture, null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name="uploads")
    qr_text = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return the uploading student and timestamp."""
        return f"{self.student} at {self.uploaded_at}"


# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------

def is_instructor(user):
    """Return True if ``user`` is authenticated and has an InstructorProfile."""
    return (user is not None and user.is_authenticated
            and InstructorProfile.objects.filter(user=user).exists())


def is_student(user):
    """Return True if ``user`` is authenticated and has a StudentProfile."""
    return (user is not None and user.is_authenticated
            and StudentProfile.objects.filter(user=user).exists())


def getUploadsForCourse(course):
    """Return QRCodeUploads for ``course``'s lectures, newest first."""
    return (QRCodeUpload.objects.filter(lecture__course=course)
            .order_by("-uploaded_at", "-id"))
