from django.contrib.admindocs.utils import parse_rst
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, status, parsers, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from courses import serializers, paginators, perms
from courses.models import Category, Course, Lesson, User, Comment, Like, Enrollment, Teacher
from courses.paginators import ItemPagination


@extend_schema(
    request={
        'multipart/form-data': serializers.UserSerializer
    }
)


class CategoryView(viewsets.ViewSet, generics.ListAPIView):
   queryset = Category.objects.all()
   serializer_class = serializers.CategorySerializer


class CourseView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
   queryset = Course.objects.filter(active=True)
   serializer_class = serializers.CourseSerializer
   pagination_class = ItemPagination
   parsers_classes = [parsers.MultiPartParser, parsers.FormParser]


   def get_queryset(self):
       query = self.queryset
       q = self.request.query_params.get('q')
       if q:
           query = query.filter(name__icontains=q)
       cate_id = self.request.query_params.get('category_id')
       if cate_id:
           query = query.filter(category_id=cate_id)

       tag_id = self.request.query_params.get('tag_id')
       if tag_id:
           query = query.filter(tags__id=tag_id)
       return query.distinct()

   def perform_create(self, serializer):
       if hasattr(self.request.user, 'teacher'):
           serializer.save(instructor=self.request.user.teacher)
       else:
           from rest_framework.exceptions import ValidationError
           raise ValidationError({"detail": "Tài khoản không có hồ sơ Giảng viên."})

   @action(methods=['get'], url_path='lessons', detail=True)
   def get_lessons(self, request, pk):
           lessons = self.get_object().lessons.filter(active=True)
           return Response(serializers.LessonSerializer(lessons, many=True).data, status=status.HTTP_200_OK)

   @action(methods=['post'], url_path='enroll', detail=True, permission_classes=[permissions.IsAuthenticated])
   def enroll(self, request, pk):
       course = self.get_object()
       user = request.user

       student = user.student
       enrollment, created = Enrollment.objects.get_or_create(
           student=student,
           course=course
       )

       if not created:
           return Response({"detail": "Bạn đã đăng ký khóa học này rồi."},status=status.HTTP_400_BAD_REQUEST)

       return Response(serializers.EnrollmentSerializer(enrollment).data,status=status.HTTP_201_CREATED)



class LessonView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Lesson.objects.prefetch_related('tags').filter(active=True)
    serializer_class = serializers.LessonDetailSerializer

    def get_permissions(self):
       if self.request.method.__eq__('POST'):
           return [permissions.IsAuthenticated()]
       return [permissions.AllowAny()]

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        if request.method.__eq__('POST'):
            s = serializers.CommentSerializer(data={
                'content': request.data.get('content'),
                'user': self.request.user.pk,
                'lesson': pk
            })
            s.is_valid(raise_exception=True)
            c = s.save()
            return Response(serializers.CommentSerializer(c).data, status=status.HTTP_201_CREATED)

        comments = self.get_object().comment_set.select_related('user').filter(active=True)

        p = paginators.CommentPaginator()
        page = p.paginate_queryset(comments, self.request)
        if page is not None:
            serializer = serializers.CommentSerializer(page, many=True)
            return p.get_paginated_response(serializer.data)

        return Response(serializers.CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='likes', detail=True)
    def get_like(self, request, pk):
        if request.method.__eq__('POST'):
            s = serializers.LikeSerializer(data={
                'user': self.request.user.pk,
            })
            s.is_valid(raise_exception=True)
            like = s.save()
            return Response(serializers.LikeSerializer(like).data, status=status.HTTP_200_OK)
        return Response(serializers.LikeSerializer(request).data, status=status.HTTP_200_OK)



class UserView(viewsets.ViewSet, generics.CreateAPIView):
   queryset = User.objects.filter(is_active=True)
   serializer_class = serializers.UserSerializer
   parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

   @swagger_auto_schema(
       method='patch',
       request_body=serializers.UserSerializer,
       responses={200: serializers.UserSerializer}
   )

   @action(methods=['get','patch' ], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
   def get_current_user(self, request):
       u = request.user
       if request.method == 'PATCH':
           serializer = serializers.UserSerializer(u, data=request.data, partial=True)
           serializer.is_valid(raise_exception=True)
           serializer.save()
           return Response(serializer.data, status=status.HTTP_200_OK)

       return Response(serializers.UserSerializer(u).data, status=status.HTTP_200_OK)

   @action(methods=['get'], url_path='my-courses', detail=False,permission_classes=[permissions.IsAuthenticated])
   def my_courses(self, request):
       user = request.user
       if user.role != User.Role.STUDENT:
           courses = Course.objects.filter(instructor=user.teacher, active=True)
           serializer = serializers.CourseSerializer(courses, many=True)
           return Response(serializer.data, status=status.HTTP_200_OK)
       else:
           enrollments = Enrollment.objects.filter(student=user.student)
           serializer = serializers.EnrollmentSerializer(enrollments, many=True)
           return Response(serializer.data)

   @action(methods=['get'], url_path='verified-teachers', detail=False)
   def get_verified_teachers(self, request):
       teachers = Teacher.objects.filter(is_verified=True, is_active=True)
       page = PageNumberPagination()
       page = self.paginate_queryset(teachers)
       if page is not None:
           serializer = serializers.UserSerializer(page, many=True)
           return self.get_paginated_response(serializer.data)

       serializer = serializers.UserSerializer(teachers, many=True)
       return Response(serializer.data, status=status.HTTP_200_OK)

   @action(methods=['get'], url_path='all-user', detail=False)
   def get_all_users(self, request):
       return Response(serializers.UserSerializer(User.objects.all(), many=True).data, status=status.HTTP_200_OK)


class CommentView(viewsets.ViewSet, generics.DestroyAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.CommentOwner]

