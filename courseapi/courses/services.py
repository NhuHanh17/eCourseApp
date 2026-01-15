from django.db import transaction
from django.db.models import Count, Sum, Q, DecimalField
from django.db.models.functions import Coalesce, TruncMonth, TruncQuarter, TruncYear
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from .models import Course, Enrollment, Transaction, User
from . import serializers


class CreateServices:
    success_message = "Thành công"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                "success": True,
                "message": self.success_message,
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )



class CourseService:
    @staticmethod
    def get_my_courses(user):
        if user.role == User.Role.TEACHER:
            courses = Course.objects.filter(instructor=user.teacher, active=True)
            serializer = serializers.CourseSerializer(courses, many=True)
            return serializer.data, status.HTTP_200_OK

        else:
            enrollments = Enrollment.objects.filter(student=user.student)
            serializer = serializers.EnrollmentSerializer(enrollments, many=True)
            return serializer.data, status.HTTP_200_OK

    @staticmethod
    def enroll_student_to_course(user, course, pay_method):
        student = getattr(user, 'student', None)
        if not student:
            raise PermissionDenied("Chỉ học sinh mới được đăng ký khóa học")

        if Enrollment.objects.filter(student=student, course=course).exists():
            return {"detail": "Bạn đã đăng ký khóa học này rồi."}, status.HTTP_400_BAD_REQUEST

        with transaction.atomic():
            enrol = Enrollment.objects.create(student=student, course=course)

            response_data = {
                "success": True,
                "message": "Đăng ký thành công!",
                "enrollment_id": enrol.id ,
                "course": serializers.CourseCreateSerializer(course).data
            }

            if course.fee > 0:
                trans = Transaction.objects.create(
                    enrollment=enrol,
                    amount=course.fee,
                    pay_method=pay_method,
                    status=True
                )
                response_data["transaction"] = serializers.TransactionSerializer(trans).data
                response_data["message"] = f"Thanh toán qua {pay_method} và đăng ký thành công!"
            else:
                response_data["message"] = "Đăng ký thành công khóa học miễn phí!"

            return response_data, status.HTTP_201_CREATED


class LecturerReportService:
    @staticmethod
    def get_financial_stats(teacher):
        return Course.objects.filter(instructor=teacher).annotate(
            total_students=Count('enrollments', distinct=True),
            total_revenue=Coalesce(
                Sum(
                    'enrollments__payment__amount',
                    filter=Q(enrollments__payment__status=True)
                ),
                Decimal('0.0'),
                output_field=DecimalField(max_digits=12, decimal_places=2) 
            )
        ).values('id', 'name', 'total_students', 'total_revenue')

    @staticmethod
    def get_revenue_stats(teacher, period='month'):
    
        trunc_func = {
            'month': TruncMonth('created_date'),
            'quarter': TruncQuarter('created_date'),
            'year': TruncYear('created_date')
        }.get(period, TruncMonth('created_date'))

        return Transaction.objects.filter(
            enrollment__course__instructor=teacher,
            status=True
        ).annotate(
            time_mark=trunc_func 
        ).values('time_mark').annotate(
            total_revenue=Sum('amount', output_field=DecimalField(max_digits=12, decimal_places=2))
        ).order_by('-time_mark')