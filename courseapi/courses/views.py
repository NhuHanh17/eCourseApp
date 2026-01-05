



from django.contrib.admindocs.utils import parse_rst
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, status, parsers, permissions
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
       if q:
           query = query.filter(name__icontains=q)
       cate_id = self.request.query_params.get('category_id')
       if cate_id:
           query = query.filter(category_id=cate_id)
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
   parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

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

