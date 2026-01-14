from django.contrib.admindocs.utils import parse_rst
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, status, parsers, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from courses import serializers, paginators, perms
from courses.models import Category, Course, Lesson, User, Comment, Like, Enrollment
from courses.models import  Teacher, Rating, Transaction, LessonStatus, Tag
from django.db.models import Count, Avg, Q, Exists, OuterRef,Value, BooleanField
from django.db.models.functions import Coalesce



from courses.paginators import ItemPagination


class CategoryView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
   queryset = Category.objects.all()
   serializer_class = serializers.CategorySerializer
   parser_classes = (parsers.MultiPartParser, parsers.FormParser)
   permission_classes = [perms.IsGiangVienOrReadOnly]

class TagView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
    queryset = Tag.objects.filter(active=True)
    serializer_class = serializers.TagSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    permission_classes = [perms.IsGiangVienOrReadOnly]

class CourseView(viewsets.ModelViewSet):
   queryset = (Course.objects.filter(active=True)
               .select_related('instructor__user_ptr', 'category')
               .prefetch_related('tags').filter(active=True)
               .annotate(
                   total_likes=Count(
                       'like',
                       filter=Q(like__active=True),
                       distinct=True
                   ),
                   avg_rating=Coalesce(
                       Avg('rating__rate'),0.0)
               ))

   serializer_class = serializers.CourseSerializer
   pagination_class = ItemPagination
   parser_classes = [parsers.MultiPartParser, parsers.FormParser]
   http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

   def get_permissions(self):
       if self.action == 'create':
           return [perms.IsVerifiedTeacher()]
       elif self.action in ['update', 'partial_update', 'destroy']:
           return [perms.IsVerifiedTeacher(), perms.IsInstructorOfCourse()]
       return [permissions.AllowAny()]

   def get_serializer_class(self):
       if self.action in ['create', 'partial_update']:
           return serializers.CourseCreateSerializer
       return self.serializer_class

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

       instructor_id = self.request.query_params.get('instructor_id')
       if instructor_id:
           query = query.filter(instructor_id=instructor_id)

       user = self.request.user
       if user.is_authenticated and hasattr(user, 'student'):
           query = query.annotate(
               is_liked_by_me=Exists(
                   Like.objects.filter(
                       course=OuterRef('pk'),
                       student=user.student,
                       active=True
                   )
               ),
               is_enrolled_by_me=Exists(
                   Enrollment.objects.filter(
                       course=OuterRef('pk'),
                       student=user.student
                   )
               )
           )
       else:
           query = query.annotate(
               is_liked_by_me=Value(False, output_field=BooleanField()),
               is_enrolled_by_me=Value(False, output_field=BooleanField())
           )

       return query.distinct()

   def perform_create(self, serializer):
       serializer.save(instructor=self.request.user.teacher)

   def perform_update(self, serializer):
       serializer.save(instructor=self.request.user.teacher)

   def destroy(self, request, *args, **kwargs):
       course = self.get_object()

       if course.duration and course.duration > 0:
           return Response(
               {"detail": "Không thể xóa(ẩn) khóa học có bài học! "},
               status=status.HTTP_400_BAD_REQUEST
           )
       course.active = False
       course.save()

       return Response(
           {"detail": "Khóa học đã được xóa(ẩn) thành công."},
           status=status.HTTP_204_NO_CONTENT
       )

   @action(methods=['get', 'post'], url_path='lessons', detail=True,
                                                serializer_class=serializers.LessonCreateSerializer)
   def get_lessons(self, request, pk):
        course = self.get_object()

        if request.method.__eq__('POST'):
            teacher_profile = getattr(request.user, 'teacher', None)

            if teacher_profile is None or course.instructor != teacher_profile:
                return Response({"detail": "Bạn không có quyền thêm bài học vào khóa học này"}
                                ,status=status.HTTP_403_FORBIDDEN)

            serializer = serializers.LessonCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(course=course)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lessons = course.lessons.filter(active=True)
        return Response(serializers.LessonSerializer(lessons, many=True).data, status=status.HTTP_200_OK)

   @action(methods=['post'], url_path='enroll', detail=True, serializer_class = serializers.EnrollmentSerializer)
   def enroll(self, request, pk):
       course = self.get_object()
       student = request.user.student

       if Enrollment.objects.filter(student=student, course=course).exists():
           return Response({"detail": "Bạn đã đăng ký khóa học này rồi."},
                                            status=status.HTTP_400_BAD_REQUEST)

       method = request.data.get('pay_method', Transaction.PayMethods.CASH)
       course_fee = getattr(course, 'fee', 0)
       try:
           with transaction.atomic():
               enrol = Enrollment.objects.create(student=student, course=course)

               if course_fee > 0:
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

               course_data = serializers.CourseSerializer(course, context={'request': request}).data

               return Response({
                   "message": "Đăng ký thành công khóa học miễn phí",
                   "enrollment_id": enrol.id,
                   "course": course_data,
               }, status=status.HTTP_201_CREATED)

       except Exception as e:
           return Response({"detail": f"Lỗi: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


   @action(methods=['post'], url_path='like', detail=True, serializer_class = serializers.LikeSerializer)
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

   @action(methods=['post'], url_path='rating', detail=True, serializer_class=serializers.RatingSerializer)
   def rate_course(self, request, pk):
       serializer = serializers.RatingSerializer(data=request.data)
       serializer.is_valid(raise_exception=True)

       rate_value = serializer.validated_data.get('rate')
       rating = Rating.objects.update_or_create(
           student=request.user.student,
           course=self.get_object(),
           defaults={'rate': rate_value}
       )
       return Response(serializers.RatingSerializer(rating).data, status=status.HTTP_200_OK)



class LessonView(viewsets.ViewSet, generics.RetrieveAPIView, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Lesson.objects.prefetch_related('tags').filter(active=True)
    serializer_class = serializers.LessonDetailSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [perms.IsInstructorOfCourse()]
        return [permissions.AllowAny()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if user.role == User.Role.TEACHER:
            if instance.course.instructor == getattr(user, 'teacher', None):
                return super().retrieve(request, *args, **kwargs)
            return Response({"detail": "Bạn không phải giảng viên của khóa học này."},
                            status=status.HTTP_403_FORBIDDEN)

        if user.role == User.Role.STUDENT:
            is_enrolled = Enrollment.objects.filter(
                student=getattr(user, 'student', None),
                course=instance.course
            ).exists()

            if is_enrolled:
                return super().retrieve(request, *args, **kwargs)

            return Response(
                {"detail": "Bạn cần đăng ký khóa học này để xem nội dung bài học."},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({"detail": "Không thể truy cập khóa học."}, status=status.HTTP_403_FORBIDDEN)


    def perform_destroy(self, instance):
        instance.active = False
        instance.save()

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
        enrollment = Enrollment.objects.filter(student=student, course=lesson.course).first()

        if enrollment:
            LessonStatus.objects.update_or_create(
                student=student, lesson=lesson,
                defaults={'is_completed': True}
            )
            enrollment.update_progress()
            return Response({
                "message": "Đã hoàn thành bài học!",
                "progress": f"{enrollment.progress}%",
                "is_completed": enrollment.is_completed
            })
        return Response({"detail": "Lỗi: Không tìm thấy khóa học đăng ký"}, status=400)


class UserView(viewsets.ViewSet, generics.CreateAPIView):
   queryset = User.objects.filter(is_active=True)
   serializer_class = serializers.UserSerializer
   parser_classes = (parsers.MultiPartParser,parsers.FormParser, parsers.JSONParser)

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

   @action(methods=['get'], url_path='chat-students', detail=False, permission_classes=[permissions.IsAuthenticated])
   def get_chat_students(self, request):
       students = User.objects.filter(
           role=User.Role.STUDENT,
           is_active=True
       ).exclude(id=request.user.id)

       serializer = serializers.ChatUserSerializer(students, many=True, context={'request': request})
       return Response(serializer.data, status=status.HTTP_200_OK)

   @action(methods=['get'], url_path='chat-teachers', detail=False, permission_classes=[permissions.IsAuthenticated])
   def get_chat_teachers(self, request):
       teachers = User.objects.filter(
           role=User.Role.TEACHER,
           is_active=True
       )

       serializer = serializers.ChatUserSerializer(teachers, many=True, context={'request': request})
       return Response(serializer.data, status=status.HTTP_200_OK)


class CommentView(viewsets.ViewSet, generics.DestroyAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.CommentOwner]



