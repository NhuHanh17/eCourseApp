from django.urls import path, re_path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import CategoryView


r = DefaultRouter()
r.register('categories', views.CategoryView, basename='category')
r.register('courses', views.CourseView, basename='course')
r.register('lessons', views.LessonView, basename='lesson')
r.register('teachers', views.TeacherView, basename='teacher')
r.register('students', views.StudentView, basename='student')

urlpatterns = [
    path('', include(r.urls)),
]