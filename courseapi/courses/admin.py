from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from courses.models import Course, Category, Teacher, Lesson, Student, Tag, Comment, Enrollment, Transaction
from django.urls import path


class LessonForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)
    class Meta:
        model = Lesson
        fields = '__all__'


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_icon', 'name', 'duration', 'category', 'fee', 'instructor','active')
    list_filter = ('category', 'instructor', 'fee')
    search_fields = ('name',)
    readonly_fields = ('duration', 'image_view', )
    filter_horizontal = ('tags',)

    def image_view(self, course):
        if course.image:
            return mark_safe(f'<img src="{course.image.url}" width="300" style="border-radius: 10px;" />')
        return "Chưa có ảnh"

    def image_icon(self, course):
        if course.image:
            return mark_safe(f'<img src="{course.image.url}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />')
        return self.name

    image_icon.short_description = "Ảnh"




class UserPhotoMixin:
    def photo_preview(self, obj):
        if obj.avatar:
            url = obj.avatar.url if hasattr(obj.avatar, 'url') else obj.avatar
            return mark_safe(f'<img src="{url}" width="120" style="border-radius: 10px; border: 2px solid #ccc;" />')
        return "Chưa có ảnh"
    photo_preview.short_description = "Avatar"


@admin.register(Teacher)
class TeacherAdmin(UserAdmin, UserPhotoMixin):
    list_display = ('username', 'email', 'is_verified', 'work_place')
    list_editable = ('is_verified',)
    search_fields = ('first_name','last_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân:', {'fields': ('first_name', 'last_name', 'email', 'avatar', 'photo_preview')}),
        ('Thông tin nghề nghiệp:', {'classes': ('collapse',),'fields': ('bio', 'work_place', 'is_verified'),}),
        ('Thời gian:', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'work_place', 'bio', 'avatar'),
        }),
    )

    readonly_fields = ('photo_preview',)


@admin.register(Student)
class StudentAdmin(UserAdmin, UserPhotoMixin):
    list_display = ('student_code', 'username', 'full_name', 'birth_date')
    search_fields = ('student_code', 'username', 'email')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    full_name.short_description = "Họ và tên"

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin sinh viên',
         {'fields': ('first_name', 'last_name', 'email', 'birth_date', 'avatar', 'photo_preview')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bắt buộc', {
            'fields': ('email', 'first_name', 'last_name', 'birth_date', 'avatar'),
        }),
    )

    readonly_fields = ('photo_preview',)

class LessonAdmin(admin.ModelAdmin):
    form = LessonForm
    list_display = ('id', 'subject', 'course', 'created_date')
    search_fields = ('subject',)
    filter_horizontal = ('tags',)


class MyAdminSite(admin.AdminSite):
    site_header = 'ECourseApp'
    site_title = 'Quản trị viên'
    index_title = 'Chào mừng đến với trang quản lý'

    def get_urls(self):
        return [path('stats-view/', self.admin_view(self.stats_view))] + super().get_urls()

    def stats_view(self, request):
        course_stats = Category.objects.annotate(
            count=Count('courses')
        ).values('name', 'count')

        total_revenue = Transaction.objects.filter(status=True).aggregate(
            total=Sum('amount')
        )['total'] or 0

        registration_trend = (
            Enrollment.objects.annotate(month=TruncMonth('created_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        course_enrollment_details = Course.objects.annotate(
            student_count=Count('enrollments')
        ).values('name', 'student_count').order_by('-student_count')[:10]

        context = {
            **self.each_context(request),
            'course_stats': course_stats,
            'total_revenue': total_revenue,
            'registration_trend': registration_trend,
            'course_enrollment_details': course_enrollment_details,
            'total_courses': Course.objects.count(),
            'total_students': Student.objects.count(),
        }
        return TemplateResponse(request, 'admin/stats.html', context)


admin_site = MyAdminSite()

admin_site.register(Course, CourseAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Teacher, TeacherAdmin)
admin_site.register(Student, StudentAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Tag)
admin_site.register(Comment)
admin_site.register(Enrollment)