from django.contrib.admindocs.utils import parse_rst
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, status, parsers, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import transaction

from courses import serializers, paginators, perms
from courses.models import Category, Course, Lesson, User, Comment, Like, Enrollment, Teacher, Rating, Transaction, LessonStatus
from courses.paginators import ItemPagination


@extend_schema(
    request={
        'multipart/form-data': serializers.UserSerializer
    }
)


class CategoryView(viewsets.ViewSet, generics.ListAPIView):
   queryset = Category.objects.all()
   serializer_class = serializers.CategorySerializer


class CourseView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.UpdateAPIView):
   queryset = Course.objects.filter(active=True)
   serializer_class = serializers.CourseSerializer
   pagination_class = ItemPagination
   parsers_classes = [parsers.MultiPartParser, parsers.FormParser]
   http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']


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

   def perform_update(self, serializer):
       serializer.save(instructor=self.request.user.teacher)


   @action(methods=['get'], url_path='lessons', detail=True)
   def get_lessons(self, request, pk):
           lessons = self.get_object().lessons.filter(active=True)
           return Response(serializers.LessonSerializer(lessons, many=True).data, status=status.HTTP_200_OK)

   @action(methods=['post'], url_path='enroll', detail=True)
   def enroll(self, request, pk):
       course = self.get_object()
       student = request.user.student

       method = request.data.get('pay_method', Transaction.PayMethods.CASH)
       course_fee = getattr(course, 'fee', 0)

       try:
           with transaction.atomic():
               enrol = Enrollment.objects.create(student=student, course=course)

               if course_fee > 0:
                   method = request.data.get('pay_method', Transaction.PayMethods.CASH)
                   if method not in Transaction.PayMethods.values:
                       return Response({"detail": "Phương thức thanh toán không hợp lệ."},
                                       status=status.HTTP_400_BAD_REQUEST)

                   trans = Transaction.objects.create(
                       enrollment=enrol,
                       amount=course_fee,
                       pay_method=method,
                       status=True
                   )

                   serializer = serializers.TransactionSerializer(trans)
                   return Response({
                       "message": f"Thanh toán qua {method} và đăng ký thành công!",
                       "data": serializer.data
                   }, status=status.HTTP_201_CREATED)

               return Response({
                   "message": "Đăng ký thành công khóa học miễn phí",
                   "enrollment_id": enrol.id
               }, status=status.HTTP_201_CREATED)

       except Exception as e:
           return Response({"detail": f"Lỗi: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


   @action(methods=['post'], url_path='like', detail=True)
   def like_course(self, request, pk):


       student = request.user.student

       li, created = Like.objects.get_or_create(student=student, course=self.get_object())

       if not created:
           li.active = not li.active
           li.save()

       return Response({
           "liked": li.active,
           "detail": "Đã thích khóa học" if li.active else "Đã bỏ thích khóa học"
       }, status=status.HTTP_200_OK)

   @action(methods=['post'], url_path='rating', detail=True)
   def rate_course(self, request, pk):
       serializer = serializers.RatingSerializer(data=request.data)
       serializer.is_valid(raise_exception=True)

       rate_value = serializer.validated_data.get('rate')
       rating, created = Rating.objects.update_or_create(
           student=request.user.student,
           course=self.get_object(),
           defaults={'rate': rate_value}
       )

       serializers.CourseSerializer(self.get_object(), context={'request': request})

       return Response(serializers.RatingSerializer(rating).data, status=status.HTTP_200_OK)



class LessonView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Lesson.objects.prefetch_related('tags').filter(active=True)
    serializer_class = serializers.LessonDetailSerializer

    def get_permissions(self):
       if self.request.method.__eq__('POST'):
           return [permissions.IsAuthenticated()]
       return [permissions.AllowAny()]

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        if request.method == 'POST':

            s = serializers.CommentSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            c = s.save(
                user=request.user,
                lesson=self.get_object()
            )
            return Response(serializers.CommentSerializer(c).data, status=status.HTTP_201_CREATED)

        comments = self.get_object().comment_set.select_related('user').filter(active=True)

        p = paginators.CommentPaginator()
        page = p.paginate_queryset(comments, request)
        if page is not None:
            serializer = serializers.CommentSerializer(page, many=True)
            return p.get_paginated_response(serializer.data)

        return Response(serializers.CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='complete', detail=True)
    def mark_completed(self, request, pk):
        lesson = self.get_object()
        student = request.user.student

        is_enrolled = Enrollment.objects.filter(student=student, course=lesson.course).exists()
        if not is_enrolled:
            return Response({"detail": "Bạn chưa đăng ký khóa học này"},
                            status=status.HTTP_403_FORBIDDEN)

        ls, created = LessonStatus.objects.update_or_create(
            student=student,
            lesson=lesson,
            defaults={'is_completed': True}
        )

        return Response({
            "message": "Bạn đã hoàn thành bài học!",
            "lesson": lesson.subject,
            "is_completed": ls.is_completed,
            "updated_date": ls.updated_date
        }, status=status.HTTP_200_OK)


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
       if request.method.__eq__('PATCH'):
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
       p = PageNumberPagination()
       page = p.paginate_queryset(teachers, request)
       if page is not None:
           serializer = serializers.UserSerializer(page, many=True)
           return self.get_paginated_response(serializer.data)

       serializer = serializers.UserSerializer(teachers, many=True)
       return Response(serializer.data, status=status.HTTP_200_OK)

   @action(methods=['get'], url_path='all-user', detail=False)
   def get_all_users(self, request):
       return Response(serializers.UserSerializer(User.objects.all(), many=True).data, status=status.HTTP_200_OK)


class EnrollmentView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Enrollment.objects.filter(active=True)
    serializer_class = serializers.EnrollmentSerializer



class CommentView(viewsets.ViewSet, generics.DestroyAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.CommentOwner]

