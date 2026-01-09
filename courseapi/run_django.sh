#!/bin/bash

echo "=== 1. Cài đặt thư viện từ requirements.txt ==="
pip install -r requirements.txt

echo "=== 2. Thực thi migrate cơ sở dữ liệu ==="
python manage.py makemigrations
python manage.py migrate

echo "=== 3. Tạo superuser ==="
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=admin@example.com
export DJANGO_SUPERUSER_PASSWORD=Admin@123
export PYTHONIOENCODING=utf-8

python manage.py createsuperuser --no-input || echo "SuperUser đã tồn tại!"

python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(username='admin').first()
if u:
    u.role = 'ADMIN' # Gán lại role là ADMIN
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print("=== Đã cập nhật quyền ADMIN cho user: admin ===")
EOF



echo "=== 4. Đang chèn dữ liệu mẫu tổng hợp cho Han ==="
python manage.py shell <<EOF

from courses.models import Category, Course, Tag, Lesson, Teacher, Student
from django.contrib.auth.models import User

# --- BƯỚC 1: TẠO GIẢNG VIÊN (Teacher kế thừa User) ---
# Dùng Teacher.objects để Django tự tạo bản ghi ở cả 2 bảng (User & Teacher)
gv, created = Teacher.objects.get_or_create(
    username='gv_thanh',
    defaults={
        'first_name': 'Thành',
        'last_name': 'Nguyễn',
        'email': 'thanh@ou.edu.vn',
        'work_place': 'Đại học Mở TP.HCM',
        'bio': 'Giảng viên khoa CNTT'
    }
)
if created:
    gv.set_password('123456')
    gv.save()

# --- BƯỚC 2: TẠO DANH MỤC & TAG ---
c1, _ = Category.objects.get_or_create(name='Công nghệ phần mềm')
c2, _ = Category.objects.get_or_create(name='Khoa học cơ bản')
c3, _ = Category.objects.get_or_create(name='Trí tuệ nhân tạo')

t1, _ = Tag.objects.get_or_create(name='techniques')
t2, _ = Tag.objects.get_or_create(name='software')
t3, _ = Tag.objects.get_or_create(name='programming')
t_math, _ = Tag.objects.get_or_create(name='math')

# Link ảnh demo (Đảm bảo có ảnh để không bị lỗi .url ở API)
img_se = 'https://res.cloudinary.com/dinusoo6h/image/upload/v1767432426/Nhap-mon-cong-nghe-phan-mem_upvlck.jpg'
img_gt = 'http://res.cloudinary.com/dinusoo6h/image/upload/v1767431852/xkyol0lnhhlayntelrb5.webp'

# --- BƯỚC 3: TẠO KHÓA HỌC (Truyền trực tiếp Object gv, c1...) ---
co1, _ = Course.objects.get_or_create(
    name='Nhập môn phần mềm',
    category=c1,
    instructor=gv,
    defaults={'image': img_se, 'description': 'Khóa học về SE', 'active': True}
)

co2, _ = Course.objects.get_or_create(
    name='Giải tích',
    category=c2,
    instructor=gv,
    defaults={'image': img_gt, 'description': 'Toán cao cấp', 'active': True}
)

# --- BƯỚC 4: TẠO BÀI HỌC ---
l1, created = Lesson.objects.get_or_create(
    subject='Tổng quan SE',
    course=co1,
    defaults={'content': 'Nội dung bài 1'}
)
if created: l1.tags.add(t1, t2)

l_gt1, created = Lesson.objects.get_or_create(
    subject='Hàm số và Giới hạn',
    course=co2,
    defaults={'content': 'Khái niệm về giới hạn'}
)
if created: l_gt1.tags.add(t_math)

print("=== Đã chèn xong dữ liệu mẫu cho sinh viên OU! ===")
EOF

echo "=== 5. Chạy server Django ==="
python manage.py runserver