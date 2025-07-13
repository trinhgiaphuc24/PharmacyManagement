from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

class RoleEnum(models.TextChoices):
    ADMIN = "admin", "Admin"
    STAFF = "employee", "Employee"
    CUSTOMER = "customer", "Customer"

class StatusEnum(models.TextChoices):
    CHO_XAC_NHAN = "pending", "Chờ xác nhận"
    DANG_GIAO_HANG = "delivering", "Đang giao hàng"
    DA_GIAO = "delivered", "Đã giao"
    DA_HUY = "canceled", "Đã hủy"

class PaymentMethodEnum(models.TextChoices):
    THANH_TOAN_QUA_VNPAY = "vnpay", "Thanh toán qua VNPay"
    THANH_TOAN_KHI_NHAN_HANG = "cod", "Thanh toán khi nhận hàng"

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=100, null=False, unique=True)

    class Meta:
        abstract = True

class User(AbstractUser):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Cho phép truy cập admin
    is_superuser = models.BooleanField(default=False)  # Super quyền
    createdAt = models.DateTimeField(auto_now_add=True, null=True)
    avatarUrl = CloudinaryField('avatar', null=True)
    userRole = models.CharField(max_length=20, choices=RoleEnum.choices,default=RoleEnum.CUSTOMER)

    def __str__(self):
        return self.username



