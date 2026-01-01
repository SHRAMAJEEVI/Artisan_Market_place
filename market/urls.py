from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.get_products, name='get_products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/approve/<int:product_id>/', views.approve_product, name='approve_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.get_cart, name='get_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('order/place/', views.place_order, name='place_order'),
    path('orders/', views.get_orders, name='get_orders'),
    path('orders/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('auth/check/', views.check_auth, name='check_auth'),
]

