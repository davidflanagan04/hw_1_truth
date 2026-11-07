from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('index.html', views.index, name='index_html'),
    path('time', views.time_view, name='time'),
    path('sum', views.sum_view, name='sum'),
    path('new', views.new_user_form, name='new'),
    path('createUser', views.createUser, name='createUser'),
    path('createCourse', views.createCourse, name='createCourse'),
    path('createLecture', views.createLecture, name='createLecture'),
    path('createQRCodeUpload', views.createQRCodeUpload, name='createQRCodeUpload'),
    path('dumpUploads', views.dumpUploads, name='dumpUploads'),
    path('new_course', views.new_course_form, name='new_course'),
    path('newCourse', views.new_course_form),
    path('new_lecture', views.new_lecture_form, name='new_lecture'),
    path('newLecture', views.new_lecture_form),
    path('new_qr_upload', views.new_qr_upload_form, name='new_qr_upload'),
    path('newQRUpload', views.new_qr_upload_form),
]
