import datetime

from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Quản trị viên"
        TEACHER = "TEACHER", "Giảng viên"
        STUDENT = "STUDENT", "Sinh viên"
    avatar = CloudinaryField(default='https://res.cloudinary.com/dinusoo6h/image/upload/v1767440746/default-avatar-icon-of-social-media-user-vector_jumkxu.jpg')
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
    access_level = models.IntegerField(default=1)
    class Meta:
        verbose_name = "Quản trị viên"


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
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    duration = models.IntegerField(default = 0, help_text="Tổng số bài học của khóa học",
                                   validators=[MinValueValidator(0)])

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='courses')
    instructor = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    tags = models.ManyToManyField(Tag, blank=True, related_name='courses')

    class Meta:
        unique_together = ('name', 'instructor', 'fee')

    def __str__(self):
        return self.name

    def update_duration(self):
        count = self.lessons.filter(active=True).count()
        self.duration = count
        self.save(update_fields=['duration'])

class Lesson(BaseModel):
    subject = models.CharField(max_length=255)
    content = RichTextUploadingField()
    video_url = models.URLField(null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.RESTRICT, related_name='lessons')
    tags = models.ManyToManyField(Tag, blank=True, related_name='lessons')

    def __str__(self):
        return self.subject

    class Meta:
        unique_together = ('subject', 'course')



class LessonInteraction(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False, blank=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        abstract = True

class CourseInteraction(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False, blank=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        abstract = True


class Comment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=False, blank=False)

    content = models.TextField()

    def __str__(self):
        return self.content

    class Meta:
        ordering = ['-created_date']


class Like(CourseInteraction):
    class Meta:
        unique_together = ('student', 'course')


class LessonStatus(LessonInteraction):
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'lesson')


class Rating(CourseInteraction):
    rate = models.SmallIntegerField(default=5,validators=[MinValueValidator(1),MaxValueValidator(5)])

    class Meta:
        unique_together = ('student', 'course')



class Enrollment(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.FloatField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course')

    def update_progress(self):
        total_lessons = self.course.duration
        if total_lessons == 0:
            return 0

        completed_count = LessonStatus.objects.filter(
                            student=self.student,
                            lesson__course=self.course,
                            is_completed=True).count()

        self.progress = round((completed_count / total_lessons) * 100, 2)

        if completed_count >= total_lessons:
            self.is_completed = True
        else:
            self.is_completed = False
        self.save()

        return self.progress


class Transaction(BaseModel):
    class PayMethods(models.TextChoices):
        CASH = 'CASH', 'Tiền mặt'
        MOMO = 'MOMO', 'Ví MoMo'
        ZALOPAY = 'ZALOPAY', 'ZaloPay'
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_method = models.CharField(max_length=50,choices=PayMethods.choices,default=PayMethods.CASH)
    status = models.BooleanField(default=False)



@receiver([post_save, post_delete], sender=Lesson)
def update_course_duration(sender, instance, **kwargs):
    instance.course.update_duration()
