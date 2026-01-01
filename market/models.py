from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    img = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_products'
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    product_name = models.CharField(max_length=200, blank=True, null=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_img = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    ordered = models.BooleanField(default=False)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, related_name='items')

    def __str__(self):
        name = self.product_name or (self.product.name if self.product else "Unknown product")
        price = self.product_price or (self.product.price if self.product else 0)
        return f"{name} - {price}"

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_artisan = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} Profile"


def get_or_create_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


class Order(models.Model):
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='orders')

    def __str__(self):
        return f"Order #{self.id} - ₹{self.total_amount}"

    class Meta:
        ordering = ['-created_at']
