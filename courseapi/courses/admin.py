from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from courses.models import Course, Category, Teacher, Lesson, Student, Tag, Comment, Enrollment



class LessonForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Lesson
        fields = '__all__'



class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_icon', 'name', 'category', 'fee', 'instructor')
    list_filter = ('category', 'instructor', 'fee')
    search_fields = ('name',)
    readonly_fields = ('image_view',)
    filter_horizontal = ('tags',)

    def image_view(self, course):
        if course.image:
            return mark_safe(f'<img src="{course.image.url}" width="300" style="border-radius: 10px;" />')
        return "Chưa có ảnh"

    def image_icon(self, course):
        if course.image:
            return mark_safe(
                f'<img src="{course.image.url}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />')
        return "No Image"

    image_icon.short_description = "Ảnh"


class UserPhotoMixin:
    def photo_preview(self, obj):
        if obj.avatar:
            # Cloudinary trả về object hoặc string tùy cách cấu hình, lấy .url cho chắc chắn
            url = obj.avatar.url if hasattr(obj.avatar, 'url') else obj.avatar
            return mark_safe(f'<img src="{url}" width="120" style="border-radius: 10px; border: 2px solid #ccc;" />')
        return "Chưa có ảnh"

    photo_preview.short_description = "Xem trước ảnh"


@admin.register(Teacher)
class TeacherAdmin(UserAdmin, UserPhotoMixin):
    list_display = ('username', 'email', 'is_verified', 'work_place')
    list_editable = ('is_verified',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {'fields': ('first_name', 'last_name', 'email', 'avatar', 'photo_preview')}),
        ('Thông tin nghề nghiệp', {
            'classes': ('collapse',),
            'fields': ('bio', 'work_place', 'is_verified'),
        }),
        ('Quyền hạn', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Ngày quan trọng', {'fields': ('last_login', 'date_joined')}),
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
         {'fields': ('student_code', 'first_name', 'last_name', 'email', 'birth_date', 'avatar', 'photo_preview')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bắt buộc', {
            'fields': ('student_code', 'email', 'first_name', 'last_name', 'birth_date', 'avatar'),
        }),
    )

    readonly_fields = ('photo_preview',)

class LessonAdmin(admin.ModelAdmin):
    form = LessonForm
    list_display = ('subject', 'course', 'created_date')
    search_fields = ('subject',)
    filter_horizontal = ('tags',)


class MyAdminSite(admin.AdminSite):
    site_header = 'HỆ THỐNG KHÓA HỌC ECourseApp'
    site_title = 'Quản trị viên Han'
    index_title = 'Chào mừng Han đến với trang quản lý'


admin_site = MyAdminSite()

admin_site.register(Course, CourseAdmin)
admin_site.register(Category)
admin_site.register(Teacher, TeacherAdmin)
admin_site.register(Student, StudentAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Tag)
admin_site.register(Comment)
admin_site.register(Enrollment)