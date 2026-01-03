from courses.models import Course, Category, Lesson, Tag, Teacher, Student, User
from rest_framework import serializers

class ImageSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['image'] = instance.image.url

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = 'id', 'name'

class CourseSerializer(ImageSerializer):
    class Meta:
        model = Course
        fields = 'id', 'name', 'category' ,'description', 'created_date', 'image'

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = 'id', 'subject', 'created_date'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class LessonDetailSerializer(LessonSerializer):
    tags = TagSerializer(many=True)
    class Meta:
        model = LessonSerializer.Meta.model
        fields = LessonSerializer.Meta.fields + ('tags','content')

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = 'id','first_name', 'last_name', 'email', 'username', 'password'

        extra_kwargs = {
            'password': {
                'write_only': True,
            }
        }
    def create(self, validated_data):
        t = Teacher(**validated_data)

        t.set_password(t.password)
        t.save()

        return t



class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = 'id', 'first_name', 'last_name', 'email', 'username', 'password', 'birth_date'

        extra_kwargs = {
            'password': {
                'write_only': True,
            }
        }
    def create(self, validated_data):
        s = Student(**validated_data)
        s.set_password(s.password)
        s.save()
        return s



