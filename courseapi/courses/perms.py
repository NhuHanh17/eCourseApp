from rest_framework import permissions
from courses.models import User, Enrollment

class CommentOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, comment):
        return super().has_permission(request, view) and request.user == comment.user


class IsGiangVienOrReadOnly(permissions.BasePermission):
    message = "Bạn không có quyền thực hiện thao tác này."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not hasattr(user, 'teacher'):
            return False

        return user.teacher.is_verified


class IsVerifiedTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'teacher') and
                request.user.teacher.is_verified
        )

class IsInstructorOfCourse(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user.teacher
        if hasattr(obj, 'course'):
            return obj.course.instructor == request.user.teacher

        return False


