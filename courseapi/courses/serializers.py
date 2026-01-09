from django.conf import settings
from django.db.models import Avg

from courses.models import Course, Category, Lesson, Tag, Teacher, Student, User, Like
from courses.models import Enrollment, Comment, Rating, Transaction
from rest_framework import serializers
from django.conf import settings

import json


class ImageSerializer(serializers.ModelSerializer):
   def to_representation(self, instance):
       ret = super().to_representation(instance)
       if instance.image:
           image_url = instance.image.url
           if image_url.startswith('http://') or image_url.startswith('https://'):
               ret['image'] = image_url
           else:
               ret['image'] = f"{settings.PUBLIC_IMAGE}{image_url}"
       else:
           ret['image'] = None
       return ret

class CategorySerializer(serializers.ModelSerializer):
   class Meta:
       model = Category
       fields = 'id', 'name'

class TagSerializer(serializers.ModelSerializer):
   class Meta:
       model = Tag
       fields = '__all__'


class CourseSerializer(ImageSerializer):
    tags = TagSerializer(many=True, read_only=True)
    total_likes = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = 'id', 'name', 'category', 'description' ,'created_date', 'image', 'tags', 'total_likes', 'avg_rating'

    def get_total_likes(self, obj):
        return obj.like_set.filter(active=True).count()

    def get_avg_rating(self, obj):
        avg = obj.rating_set.aggregate(Avg('rate'))['rate__avg']
        return round(avg, 1) if avg else 0



class CourseCreateSerializer(CourseSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    instructor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        fields = CourseSerializer.Meta.fields + ('instructor',)
        extra_kwargs = {
            'image': {'required': False},
        }


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = 'id', 'subject', 'created_date'
        depth = 1


class LessonDetailSerializer(LessonSerializer):
    tags = TagSerializer(many=True)
    class Meta:
        model = LessonSerializer.Meta.model
        fields = LessonSerializer.Meta.fields + ('tags','content')


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = (
           'bio',
           'work_place',
           'is_verified',
        )
        extra_kwargs = {
            'is_verified': {'read_only': True},
        }

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = (
            'student_code',
            'birth_date',
        )
        extra_kwargs = {
            'student_code': {'read_only': True},
        }


class UserSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(required=False)
    student = StudentSerializer(required=False)

    class Meta:
        model = User
        fields = (
           'id',
           'username',
           'email',
           'password',
           'first_name',
           'last_name',
           'role',
           'avatar',
           'teacher',
           'student',
        )

        extra_kwargs = {
           'password': {'write_only': True},
        }

    def create(self, validated_data):
        role = validated_data.get("role")

        teacher_data = validated_data.pop("teacher", {})
        student_data = validated_data.pop("student", {})


        if role == User.Role.STUDENT:
            student = Student.objects.create_user(
               username=validated_data["username"],
               password=validated_data["password"],
               email=validated_data.get("email"),
               first_name=validated_data.get("first_name"),
               last_name=validated_data.get("last_name"),
               birth_date=student_data.get("birth_date"),
            )
            return student


        if role == User.Role.TEACHER:
            teacher = Teacher.objects.create_user(
               username=validated_data["username"],
               password=validated_data["password"],
               email=validated_data.get("email"),
               first_name=validated_data.get("first_name"),
               last_name=validated_data.get("last_name"),
               bio=teacher_data.get("bio"),
               work_place=teacher_data.get("work_place"),
               is_verified=False)
            return teacher


    def to_internal_value(self, data):
        data = data.dict()
        for field in ['teacher', 'student']:
            if field in data and isinstance(data[field], str):
                data[field] = json.loads(data[field])
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        for attr in ['first_name', 'last_name', 'email', 'avatar']:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        if instance.role == User.Role.TEACHER:
            teacher_data = validated_data.pop('teacher', None)
            if teacher_data and hasattr(instance, 'teacher'):
                serializer = TeacherSerializer(instance.teacher, data=teacher_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

        elif instance.role == User.Role.STUDENT:
            student_data = validated_data.get('student')
            if student_data and hasattr(instance, 'student'):
                serializer = StudentSerializer(instance.student, data=student_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        avatar = getattr(instance, 'avatar', None)

        if hasattr(avatar, 'url'):
            data['avatar'] = avatar.url
        else:
            data['avatar'] = ''
        if instance.role == User.Role.TEACHER and 'teacher' in data and data['teacher']:
            teacher_info = data.pop('teacher')
            data.update(teacher_info)

        elif instance.role == User.Role.STUDENT and 'student' in data and data['student']:
            student_info = data.pop('student')
            data.update(student_info)

        data.pop('teacher', None)
        data.pop('student', None)
        return data


class UserDataSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['user'] = UserSerializer(instance.user).data
        return data


class CommentSerializer(UserDataSerializer):
    lesson = LessonSerializer(read_only=True)
    user = UserSerializer(required=False)
    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_date', 'user', 'lesson']
        extra_kwargs = {
            'lesson': {
                'write_only': "True"
            }
        }


class LikeSerializer(UserDataSerializer):
    class Meta:
        model = Like
        fields = ('id', 'user', 'lesson')
        extra_kwargs = {
            'lesson' :{
                'write_only': "True"
            }
        }

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    class Meta:
           model = Enrollment
           fields = ['id', 'course','student','created_date', 'progress', 'is_completed']

class RatingSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    class Meta:
        model = Rating
        fields = ['id','rate', 'created_date', 'course']


class TransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='enrollment.student.user.get_full_name')
    pay_method_display = serializers.CharField(source='get_pay_method_display', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'pay_method', 'pay_method_display', 'status', 'student_name', 'created_date']