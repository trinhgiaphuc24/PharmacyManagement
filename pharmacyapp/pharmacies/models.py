from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

class RoleEnum(models.TextChoices):
    ADMIN = "admin", "Admin"
    STAFF = "employee", "Employee"
    CUSTOMER = "customer", "Customer"

class StatusEnum(models.TextChoices):
    CHO_XAC_NHAN = "pending", "Chờ xác nhận"
    CHO_LAY_HANG = "waiting_for_pickup", "Chờ lấy hàng"
    CHO_GIAO_HANG = "waiting_for_delivery", "Chờ giao hàng"
    DA_GIAO = "delivered", "Đã giao"
    TRA_HANG = "returned", "Trả hàng"
    DA_HUY = "canceled", "Đã hủy"

class PaymentMethodEnum(models.TextChoices):
    THANH_TOAN_QUA_VNPAY = "vnpay", "Thanh toán qua VNPay"
    THANH_TOAN_KHI_NHAN_HANG = "cod", "Thanh toán khi nhận hàng"

class FormatEnum(models.TextChoices):
    HOP = "hop", "Hộp"
    CHAI = "chai", "Chai"
    TUYP = "tuyp", "Tuýp"
    CAI = "cai", "Cái"

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


class MedicineGenre(BaseModel):
    imgMedicineGenreUrl = CloudinaryField(null=True)
    def __str__(self):
        return self.name

class Produce(BaseModel):

    def __str__(self):
        return self.name

class Medicine(BaseModel):
    description = models.TextField(null=True, blank=True)
    ingredient = models.TextField(null=True, blank=True)
    price = models.FloatField()
    benefit = models.TextField(null=True, blank=True)
    use = models.TextField(null=True, blank=True)
    format = models.CharField(max_length=20, choices=FormatEnum.choices,default=FormatEnum.HOP)
    note = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, null=True)
    medicineGenre = models.ForeignKey(MedicineGenre, on_delete=models.PROTECT,null=True,blank=True, related_name="genreMedicines")
    produce = models.ForeignKey(Produce, on_delete=models.PROTECT,null=True,blank=True, related_name="produces")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class MedicineImage(models.Model):
    imgMedicineUrl = CloudinaryField(null=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, null=True, blank=True,related_name="images")

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"

class Order(models.Model):
    date = models.DateField()
    status = models.CharField(max_length=20, choices=StatusEnum.choices,default=StatusEnum.CHO_XAC_NHAN)
    createdAt = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=255)
    paymentMethod = models.CharField(max_length=20, choices=PaymentMethodEnum.choices,default=PaymentMethodEnum.THANH_TOAN_QUA_VNPAY)
    total = models.FloatField()
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="order", null=True)

class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="details")
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, related_name="orderDetails", null=True)
    quantity = models.IntegerField(default=1)
    price = models.FloatField()


class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_history", null=True, blank=True)
    user_message = models.TextField()
    bot_response = models.TextField()
    session_id = models.CharField(max_length=100, null=True, blank=True)  # Cho anonymous users
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Chat {self.id} - {self.created_at}"



