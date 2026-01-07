from courses.models import Course, Category, Lesson, Tag, Teacher, Student, User, Like
from courses.models import Enrollment, Comment, Transaction
from rest_framework import serializers
import json


class ImageSerializer(serializers.ModelSerializer):
   def to_representation(self, instance):
       ret = super().to_representation(instance)
       ret['image'] = instance.image.url
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
    class Meta:
        model = Course
        fields = 'id', 'name', 'category', 'description' ,'created_date', 'image', 'tags'




class CourseCreateSerializer(CourseSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    instructor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        fields = CourseSerializer.Meta.fields + ('instructor',)
        extra_kwargs = {
            'image': {'required': False},
        }

    def get_image(self, instance):
        if instance.image:
            # Nếu là Cloudinary hoặc ImageField, trả về url.
            # Nếu đã là string (do default), trả về chính nó.
            if hasattr(instance.image, 'url'):
                return instance.image.url
            return str(instance.image)
        return None



class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = 'id', 'subject', 'created_date'


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
   class Meta:
       model = Enrollment
       fields = ['id', 'course', 'student', 'created_date', 'progress', 'is_completed']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

