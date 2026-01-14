from django.conf import settings
from django.db.models import Avg
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from courses.models import Course, Category, Lesson, Tag, Teacher, Student, User, Like, LessonStatus
from courses.models import Enrollment, Comment, Rating, Transaction
from rest_framework import serializers


import json


class ImageSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url

        return data


class AvatarSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url
        return data

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

    # Nếu Teacher kế thừa User
    instructor_name = serializers.CharField(
        source='instructor.get_full_name',
        read_only=True
    )

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'category', 'description', 'duration', 'fee',
            'instructor_name',
            'created_date', 'image', 'tags',
            'total_likes', 'avg_rating'
        ]

    def get_total_likes(self, obj):
        return obj.like_set.filter(active=True).count()

    def get_avg_rating(self, obj):
        avg = obj.rating_set.aggregate(Avg('rate'))['rate__avg']
        return round(avg, 1) if avg else 0



class CourseCreateSerializer(CourseSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    instructor = serializers.PrimaryKeyRelatedField(read_only=True)
    image = serializers.ImageField(required=False)

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['instructor']
        extra_kwargs = {
            'image': {'required': False},
            'duration': {'read_only': True},
            'description': {'required': False},
        }

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'teacher'):
            raise ValidationError("Người dùng hiện tại không phải là giảng viên.")

        instructor = request.user.teacher
        name = attrs.get('name')
        fee = attrs.get('fee')

        instance = self.instance
        queryset = Course.objects.filter(instructor=instructor, name=name, fee=fee)

        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise ValidationError({
                "non_field_errors": ["Bạn đã có một khóa học với tên và mức giá này rồi!"]
            })
        return attrs


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = 'id', 'subject', 'created_date'


class LessonDetailSerializer(LessonSerializer):
    tags = TagSerializer(many=True)
    class Meta:
        model = LessonSerializer.Meta.model
        fields = LessonSerializer.Meta.fields + ('tags','content')

class LessonCreateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)

    class Meta(LessonSerializer.Meta):
        fields = LessonSerializer.Meta.fields + ('content', 'tags')
        extra_kwargs = {
            'created_date': {'read_only': True},
        }

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        lesson = Lesson.objects.create(**validated_data)
        lesson.tags.set(tags)
        return lesson


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ('bio', 'work_place', 'is_verified')
        read_only_fields = ('is_verified',)


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ('student_code', 'birth_date')
        read_only_fields = ('student_code',)




class UserSerializer(AvatarSerializer):

    teacher = TeacherSerializer(required=False)
    student = StudentSerializer(required=False)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'role', 'avatar',
            'teacher', 'student'
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()

        for field in ['teacher', 'student']:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    pass
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):

        teacher_data = validated_data.pop('teacher', None)
        student_data = validated_data.pop('student', None)
        role = validated_data.get('role')

        if role == User.Role.TEACHER:
            user = Teacher.objects.create_user(**validated_data, **(teacher_data or {}))
        elif role == User.Role.STUDENT:
            user = Student.objects.create_user(**validated_data, **(student_data or {}))
        else:
            user = User.objects.create_user(**validated_data)

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        teacher_data = validated_data.pop('teacher', None)
        student_data = validated_data.pop('student', None)

        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()


        if instance.role == User.Role.TEACHER and teacher_data:
            Teacher.objects.filter(pk=instance.pk).update(**teacher_data)
        elif instance.role == User.Role.STUDENT and student_data:
            Student.objects.filter(pk=instance.pk).update(**student_data)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        role_map = {
            User.Role.TEACHER: 'teacher',
            User.Role.STUDENT: 'student'
        }

        profile_key = role_map.get(instance.role)
        if profile_key and data.get(profile_key):
            profile_data = data.pop(profile_key)
            data.update(profile_data)

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

class LikeSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ['id', 'student', 'active', 'created_date']
        read_only_fields = ['active', 'student']

    def get_student(self, obj):
        user = obj.student.user
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
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


class ChatUserSerializer(AvatarSerializer):
    full_name = serializers.ReadOnlyField(source='get_full_name')

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar', 'role']
