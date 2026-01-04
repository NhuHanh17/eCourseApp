from django.contrib.admindocs.utils import parse_rst
from rest_framework import viewsets, generics, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from courses import serializers, paginators

from courses.models import Category, Course, Lesson, Teacher, Student, User
from courses.paginators import ItemPagination


class CategoryView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer

class CourseView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Course.objects.filter(active=True)
    serializer_class = serializers.CourseSerializer
    pagination_class = ItemPagination

    def get_queryset(self):
        query = self.queryset
        q = self.request.query_params.get('q')
        print(q)
        if q:
            query = query.filter(name__icontains=q)
        cate_id = self.request.query_params.get('category_id')
        if cate_id:
            query = query.filter(category_id=cate_id)
        print("final: ")
        print (query)
        return query

    @action(methods=['get'], url_path='lessons', detail=True)
    def get_lessons(self, request, pk):
            lessons = self.get_object().lessons.filter(active=True)

            return Response(serializers.LessonSerializer(lessons, many=True).data, status=status.HTTP_200_OK)


class LessonView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Lesson.objects.prefetch_related('tags').filter(active=True)
    serializer_class = serializers.LessonDetailSerializer


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser]

    @action(methods=['get'], url_path='current-user', detail=False )
    def get_current_user(self, request):
        return Response(serializers.UserSerializer(request.user).data, status=status.HTTP_200_OK)




class TeacherView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Teacher.objects.filter(is_active=True)
    serializer_class = serializers.TeacherSerializer
    parser_classes = [parsers.MultiPartParser]


    @action(methods=['get'], url_path='current-teacher', detail=False )
    def get_current_teacher(self, request):
        return Response(serializers.TeacherSerializer(request.user).data, status=status.HTTP_200_OK)

class StudentView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Student.objects.filter(is_active=True)
    serializer_class = serializers.StudentSerializer
    parser_classes = [parsers.MultiPartParser]