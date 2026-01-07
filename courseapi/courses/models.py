import datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField


# ==========================================================
# 1. HỆ THỐNG USER KẾ THỪA (Inheritance)
# ==========================================================

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Quản trị viên"
        TEACHER = "TEACHER", "Giảng viên"
        STUDENT = "STUDENT", "Sinh viên"
    avatar = CloudinaryField(default='https://res.cloudinary.com/dinusoo6h/image/upload/v1767440746/default-avatar-icon-of-social-media-user-vector_jumkxu.jpg')
    # avatar = models.ImageField(default='https://res.cloudinary.com/dinusoo6h/image/upload/v1767440746/default-avatar-icon-of-social-media-user-vector_jumkxu.jpg', upload_to='avatar/%Y/%m/')
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT
    )

    def __str__(self):
        return self.username


class Teacher(User):
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(null=True, blank=True)
    work_place = models.CharField(max_length=255, null=True, blank=True)
    role = User.Role.TEACHER

    def save(self, *args, **kwargs):
        self.role = User.Role.TEACHER
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Giảng viên"

    def __str__(self):
        return self.first_name + " " + self.last_name


class Student(User):
    student_code = models.CharField(max_length=20, unique=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.role = User.Role.STUDENT
        if not self.student_code:
            year = datetime.datetime.now().year
            last_student = Student.objects.filter(student_code__startswith=f"SV{year}").order_by(
                "-student_code").first()

            if last_student:
                last_number = int(last_student.student_code[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.student_code = f"SV{year}{new_number:04d}"

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Sinh viên"


class AdminProfile(User):
    """ Kế thừa từ User: Chứa thông tin Quản trị viên """
    access_level = models.IntegerField(default=1)
    class Meta:
        verbose_name = "Quản trị viên"


# ==========================================================
# 2. CÁC MODEL QUẢN LÝ KHÓA HỌC
# ==========================================================

class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self): return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self): return self.name


class Course(BaseModel):
    name = models.CharField(max_length=255)
    description = RichTextField()
    video_url = models.URLField(null=True,blank=True,
                            help_text="Trailer cho khoá học (link youtube hoặc video)")
    image = CloudinaryField(null=True, blank=True, default="https://res.cloudinary.com/dinusoo6h/image/upload/v1767792152/Gemini_Generated_Image_enqxopenqxopenqx_s7tmxb.png")
    # mage = models.ImageField(upload_to="courses/%Y/%m", null=True, blank=True, default='https://res.cloudinary.com/dinusoo6h/image/upload/v1767792152/Gemini_Generated_Image_enqxopenqxopenqx_s7tmxb.png')
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    duration = models.IntegerField(default = 0, help_text="Tổng số bài học của khóa học",
                                   validators=[MinValueValidator(0)])

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='courses')
    instructor = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    tags = models.ManyToManyField(Tag, blank=True, related_name='courses')

    def __str__(self):
        return self.name

class Lesson(BaseModel):
    subject = models.CharField(max_length=255)
    content = RichTextField()
    video_url = models.URLField(null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.RESTRICT, related_name='lessons')
    tags = models.ManyToManyField(Tag, blank=True, related_name='lessons')

    def __str__(self):
        return self.subject

    class Meta:
        unique_together = ('subject', 'course')


# ==========================================================
# 3. TƯƠNG TÁC KẾ THỪA
# ==========================================================

class Interaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        abstract = True


class Comment(Interaction):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=False, blank=False)
    content = models.TextField()

    def __str__(self):
        return self.content

class Like(Interaction):
    class Meta:
        unique_together = ('user', 'course')


class Rating(Interaction):
    rate = models.IntegerField(default=5)


# ==========================================================
# 4. ĐĂNG KÝ & THANH TOÁN
# ==========================================================

class Enrollment(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.FloatField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course')


class Transaction(BaseModel):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_method = models.CharField(max_length=50)
    status = models.BooleanField(default=False)