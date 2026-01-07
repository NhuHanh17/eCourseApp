from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.utils.safestring import mark_safe
from courses.models import Course, Category, Teacher, Lesson, Student, Tag, Comment, Like


class LessonForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Lesson
        fields = '__all__'


class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'duration', 'fee', 'instructor' )
    list_filter = ('category', 'instructor','fee')
    search_fields = ('name',)
    readonly_fields = ('image_view',)

    def image_view(self, course):
        if course.image:
            return mark_safe(f'<img src="{course.image.url}" width="200" />')


@admin.register(Teacher)
class TeacherAdmin(UserAdmin):

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_verified')
    list_editable = (
        "is_verified",
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin Giảng viên', {'fields': ('bio', 'work_place')}),
    )

    # Cấu hình các trường khi nhấn "Add" (Tạo mới)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin Giảng viên', {
            'classes': ('wide',),
            'fields': ('bio', 'work_place', 'role'),  # Đảm bảo có role Han vừa thêm
        }),
    )


@admin.register(Student)
class StudentAdmin(UserAdmin):
    list_display = ('username', 'email', 'student_code')
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin Sinh viên', {'fields': ('student_code', 'birth_date')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin Sinh viên', {
            'fields': ('student_code', 'birth_date', 'role'),
        }),
    )

class LessonAdmin(admin.ModelAdmin):
    form = LessonForm


class MyAdminSite(admin.AdminSite):
    site_header = 'eCourseApp'

    # def get_urls(self):
    #     return [path('/course-stats'), self.stats_view] + super().get_urls()
    # def stats_view(self, request):
    #     pass


admin_site = MyAdminSite()


admin_site.register(Course, CourseAdmin)
admin_site.register(Category)
admin_site.register(Teacher, TeacherAdmin)
admin_site.register(Student, StudentAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Tag)
admin_site.register(Comment)
admin_site.register(Like)