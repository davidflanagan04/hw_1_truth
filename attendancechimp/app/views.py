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
from django.contrib.auth import authenticate, login
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



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



