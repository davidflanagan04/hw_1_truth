"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from PIL import Image
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from datetime import datetime
import zoneinfo
import json
import io

from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
                    Lecture, QRCodeUpload, is_instructor, is_student,
                      getUploadsForCourse)

CDT = zoneinfo.ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html)."""
    now = datetime.now(CDT)
    user_name = None
    if request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.get_username()
    context = {
        "current_time": now.strftime("%H:%M"),
        "user_name": user_name,
    }
    return render(request, 'app/index.html', context)

def time_view(request):
    """Return the current Central time as plain text, formatted HH:MM."""
    now = datetime.now(CDT)
    return HttpResponse(now.strftime("%H:%M"), content_type="text/plain")

def sum_view(request):
    """Return <p>{"sum": n1 + n2}</p> for GET parameters n1 and n2."""
    def to_number(s):
        try:
            return int(s)
        except ValueError:
            return float(s)

    try:
        n1 = to_number(request.GET["n1"])
        n2 = to_number(request.GET["n2"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest("n1 and n2 must be numbers")

    return HttpResponse(f"<p>{n1 + n2}</p>", content_type="text/html")

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------

@require_GET
def new_user_form(request):
    """Render the sign-up form. Non-GET requests get 405."""
    return render(request, 'app/new.html')

@csrf_exempt
@require_POST
def createUser(request):
    """Create a User plus Student/Instructor profile, log them in."""
    email = request.POST.get("email", "").strip()
    user_name = request.POST.get("user_name", "").strip()
    password = request.POST.get("password", "")
    is_student_raw = request.POST.get("is_student", "")

    if not (email and user_name and password and is_student_raw):
        return HttpResponseBadRequest("email, user_name, password and is_student are required")

    # Accept 1/true (curl and form) as student, anything else as instructor
    student = is_student_raw.strip().lower() in ("1", "true", "yes", "on")

    if User.objects.filter(email__iexact=email).exists():
        return HttpResponseBadRequest("A user with that email already exists")
    if User.objects.filter(username=user_name).exists():
        return HttpResponseBadRequest("A user with that user name already exists")

    user = User.objects.create_user(username=user_name, email=email, password=password)

    if student:
        # student_id (CNetID) is unique and required; use the unique user name
        StudentProfile.objects.create(user=user, student_id=user_name)
    else:
        InstructorProfile.objects.create(user=user)

    login(request, user)
    return HttpResponse("User created", content_type="text/plain")

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------

@require_GET
def new_course_form(request):
    """Render the course-creation form for a logged-in user."""
    return render(request, 'app/new_course.html')

COURSE_DAYS = [("day-mon", "Mon"), ("day-tue", "Tue"), ("day-wed", "Wed"),
               ("day-thu", "Thu"), ("day-fri", "Fri")]

@csrf_exempt
@require_POST
def createCourse(request):
    """Create a Course for the logged-in instructor (401 if not an instructor)."""
    if not is_instructor(request.user):
        return HttpResponse("Instructor login required", status=401,
                            content_type="text/plain")

    name = request.POST.get("course-name", "").strip()
    start_raw = request.POST.get("start-time", "").strip()
    end_raw = request.POST.get("end-time", "").strip()
    days = [label for field, label in COURSE_DAYS
            if request.POST.get(field, "").strip().lower() in ("1", "true", "yes", "on")]

    if not (name and start_raw and end_raw and days):
        return HttpResponseBadRequest(
            "course-name, start-time, end-time and at least one day-* field are required")

    try:
        start = datetime.strptime(start_raw, "%H:%M")
        end = datetime.strptime(end_raw, "%H:%M")
    except ValueError:
        return HttpResponseBadRequest("start-time and end-time must be HH:MM")
    if end <= start:
        return HttpResponseBadRequest("end-time must be after start-time")

    meeting_schedule = f"{','.join(days)} {start_raw}-{end_raw}"
    course = Course.objects.create(
        name=name, meeting_schedule=meeting_schedule,
        instructor=request.user.instructor_profile)
    return HttpResponse(f"Course created: {course.id}", content_type="text/plain")

@csrf_exempt
@require_POST
def createLecture(request):
    """Create a Lecture dated today for the named course (401 if not an instructor)."""
    if not is_instructor(request.user):
        return HttpResponse("Instructor login required", status=401,
                            content_type="text/plain")

    choice = request.POST.get("choice", "").strip()
    if not choice:
        return HttpResponseBadRequest("choice (course name) is required")

    course = Course.objects.filter(name=choice).first()
    if course is None:
        return HttpResponseBadRequest("No course with that name")
    if course.instructor.user_id != request.user.id:
        return HttpResponseForbidden("You do not teach that course")

    lecture = Lecture.objects.create(course=course, date=datetime.now(CDT).date())
    return HttpResponse(f"Lecture created: {lecture.id}", content_type="text/plain")

@csrf_exempt
@require_POST
def createQRCodeUpload(request):
    """Store an uploaded QR-code image for the logged-in student (401 if not a student)."""
    if not is_student(request.user):
        return HttpResponse("Student login required", status=401,
                            content_type="text/plain")

    image = request.FILES.get("imageUpload")
    if image is None:
        return HttpResponseBadRequest("imageUpload file is required")

    try:
        Image.open(image).verify()
    except Exception:
        return HttpResponseBadRequest("imageUpload must be a valid image")
    image.seek(0)

    # Decoding the QR text and matching it to a lecture is not done yet, so
    # qr_text stays empty and lecture stays null.
    upload = QRCodeUpload(student=request.user.student_profile, qr_text="")
    upload.image.save(image.name, image, save=False)
    upload.save()
    return HttpResponse(f"Upload created: {upload.id}", content_type="text/plain")

@require_GET
def dumpUploads(request):
    """Return every QR upload as [{"username", "upload_time"}] (401 if not an instructor)."""
    if not is_instructor(request.user):
        return HttpResponse("Instructor login required", status=401,
                            content_type="text/plain")

    uploads = QRCodeUpload.objects.select_related("student__user").order_by("uploaded_at", "id")
    data = [{"username": u.student.user.username,
             "upload_time": u.uploaded_at.astimezone(CDT).strftime("%Y-%m-%d %H:%M:%S")}
            for u in uploads]
    return JsonResponse(data, safe=False)

@require_GET
def new_lecture_form(request):
    """Render the lecture-creation form, listing the user's courses if an instructor."""
    courses = Course.objects.none()
    if is_instructor(request.user):
        courses = Course.objects.filter(instructor__user=request.user)
    return render(request, 'app/new_lecture.html', {"courses": courses})

@require_GET
def new_qr_upload_form(request):
    """Render the QR-code upload form for a logged-in user."""
    return render(request, 'app/new_qr_upload.html')



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



@require_GET
def getUploads(request):
    """Return valid uploads for ?course=<number> as [{"username", "upload_time"}] (401 if not an instructor)."""
    if not is_instructor(request.user):
        return HttpResponse("Instructor login required", status=401,
                            content_type="text/plain")

    course = request.GET.get("course", "").strip()
    if not course:
        return JsonResponse({"error": "Missing course parameter"}, status=400)

    data = [{"username": u.student.user.username,
             "upload_time": u.uploaded_at.astimezone(CDT).strftime("%Y-%m-%d %H:%M:%S")}
            for u in getUploadsForCourse(course)]
    return JsonResponse(data, safe=False)
