from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Product, CartItem, Order, get_or_create_user_profile
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
import os
import json


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication class that skips CSRF enforcement for API endpoints."""
    def enforce_csrf(self, request):
        return


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def index(request):
    """Serve the main index page"""
    return render(request, 'index.html')


def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            get_or_create_user_profile(user)
            return redirect('index')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')


def register_view(request):
    """Registration page"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        is_artisan = request.POST.get('is_artisan') == 'on'
        
        if password != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password)
        profile = get_or_create_user_profile(user)
        profile.is_artisan = is_artisan
        profile.save()
        login(request, user)
        return redirect('index')
    
    return render(request, 'register.html')


def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('login')


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
def get_products(request):
    """Get all products with ownership info"""
    products = Product.objects.all().select_related('user', 'approved_by')

    if not request.user.is_authenticated:
        products = products.filter(is_approved=True)
    elif not _is_admin(request.user):
        products = products.filter(Q(is_approved=True) | Q(user=request.user))

    products_data = []
    for p in products:
        owned = request.user.is_authenticated and p.user_id == request.user.id
        products_data.append({
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'img': p.img,
            'owner': p.user.username if p.user_id else None,
            'owned': owned,
             'is_approved': p.is_approved,
             'approved_at': p.approved_at.isoformat() if p.approved_at else None,
             'approved_by': p.approved_by.username if p.approved_by else None,
        })
    return Response(products_data)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
def add_product(request):
    """Add a new product (restricted to artisans or admins)"""
    if not request.user.is_authenticated:
        return Response(
            {'success': False, 'error': 'Please login to add products.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    profile = get_or_create_user_profile(request.user)
    if not profile.is_artisan and not _is_admin(request.user):
        return Response(
            {'success': False, 'error': 'Only registered village artisans can add products.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        name = request.data.get('name')
        price = request.data.get('price')
        img = request.data.get('img')
        
        if not name or not price or not img:
            return Response({
                'success': False,
                'error': 'Name, price, and image URL are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        price_value = Decimal(str(price))
        if price_value <= 0:
            return Response({
                'success': False,
                'error': 'Price must be greater than zero'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product = Product.objects.create(
            name=name,
            price=price_value,
            img=img,
            user=request.user,
            is_approved=_is_admin(request.user),
            approved_at=timezone.now() if _is_admin(request.user) else None,
            approved_by=request.user if _is_admin(request.user) else None,
        )
        
        return Response({
            'success': True,
            'message': 'Product submitted for approval' if not product.is_approved else 'Product added successfully',
            'product_id': product.id
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
def approve_product(request, product_id):
    """Approve a pending product (admin only)."""
    if not _is_admin(request.user):
        return Response(
            {'success': False, 'error': 'Only admins can approve products.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    product = get_object_or_404(Product, id=product_id)
    product.is_approved = True
    product.approved_at = timezone.now()
    product.approved_by = request.user
    product.save(update_fields=['is_approved', 'approved_at', 'approved_by'])

    return Response({'success': True, 'message': 'Product approved.'})

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
def add_to_cart(request):
    """Add product to cart (requires authentication)"""
    if not request.user.is_authenticated:
        return Response({
            'success': False,
            'error': 'Please login to add items to your cart.'
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({
                'success': False,
                'error': 'Product ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        if not product.is_approved and not _is_admin(request.user):
            return Response(
                {
                    'success': False,
                    'error': 'This product is pending approval and cannot be added to cart yet.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        cart_item = CartItem.objects.create(
            product=product,
            product_name=product.name,
            product_price=product.price,
            product_img=product.img,
            user=request.user
        )
        
        return Response({
            'success': True,
            'message': 'Product added to cart',
            'cart_item_id': cart_item.id
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
def get_cart(request):
    """Get all cart items"""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, ordered=False, order__isnull=True)
    else:
        session_id = request.GET.get('session_id', 'default')
        cart_items = CartItem.objects.filter(session_id=session_id, user__isnull=True, ordered=False, order__isnull=True)
    
    cart_data = []
    total = Decimal('0.00')
    
    for item in cart_items:
        cart_data.append({
            'id': item.id,
            'product_id': item.product.id if item.product else None,
            'name': item.product_name or (item.product.name if item.product else None),
            'price': float(item.product_price) if item.product_price is not None else (float(item.product.price) if item.product else 0.0),
            'img': item.product_img or (item.product.img if item.product else None)
        })
        if item.product_price is not None:
            total += item.product_price
        elif item.product:
            total += item.product.price
    
    return Response({
        'items': cart_data,
        'total': float(total)
    })


@csrf_exempt
@api_view(['DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
def remove_from_cart(request, cart_item_id):
    """Remove item from cart (supports authenticated users and guest sessions)"""
    try:
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=cart_item_id, user=request.user)
        else:
            session_id = request.GET.get('session_id') or request.data.get('session_id')
            if not session_id:
                return Response({
                    'success': False,
                    'error': 'Session ID is required for guest users'
                }, status=status.HTTP_400_BAD_REQUEST)
            cart_item = get_object_or_404(
                CartItem,
                id=cart_item_id,
                session_id=session_id,
                user__isnull=True
            )

        cart_item.delete()
        
        return Response({
            'success': True,
            'message': 'Item removed from cart'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
def place_order(request):
    """Place an order"""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        session_id = request.data.get('session_id', 'default')
        cart_items = CartItem.objects.filter(session_id=session_id, user__isnull=True)
    
    try:
        if not cart_items.exists():
            return Response({
                'success': False,
                'error': 'Cart is empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate total
        total = sum(item.product.price for item in cart_items)
        
        # Create order
        session_id = request.data.get('session_id', 'default')
        order = Order.objects.create(
            total_amount=total, 
            session_id=session_id if not request.user.is_authenticated else None,
            user=request.user if request.user.is_authenticated else None
        )
        order.items.set(cart_items)
        
        # Delete cart items after order is placed
        cart_items.delete()
        
        return Response({
            'success': True,
            'message': 'Order placed successfully',
            'order_id': order.id,
            'total': float(total)
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
def get_orders(request):
    """Get all orders for the authenticated user"""
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        session_id = request.GET.get('session_id', 'default')
        orders = Order.objects.filter(session_id=session_id, user__isnull=True)
    
    orders_data = []
    for order in orders:
        items_list = []
        for item in order.items.all():
            items_list.append({
                'id': item.id,
                'name': item.product.name,
                'price': float(item.product.price),
                'img': item.product.img
            })
        
        orders_data.append({
            'id': order.id,
            'total': float(order.total_amount),
            'created_at': order.created_at.isoformat(),
            'items': items_list
        })
    
    return Response(orders_data)


@csrf_exempt
@api_view(['DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
def delete_order(request, order_id):
    """Delete an order (requires authentication)"""
    if not request.user.is_authenticated:
        return Response({
            'success': False,
            'error': 'Authentication required to delete orders'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.delete()
        
        return Response({
            'success': True,
            'message': 'Order deleted successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
def check_auth(request):
    """Check if user is authenticated"""
    profile = get_or_create_user_profile(request.user) if request.user.is_authenticated else None
    return Response({
        'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'is_artisan': profile.is_artisan if profile else False,
        'is_admin': _is_admin(request.user),
    })


@csrf_exempt
@api_view(['DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
def delete_product(request, product_id):
    """Delete a product only if the authenticated user is the owner"""
    if not request.user.is_authenticated:
        return Response({
            'success': False,
            'error': "Authentication required"
        }, status=status.HTTP_401_UNAUTHORIZED)
    try:
        product = get_object_or_404(Product, id=product_id)
        if product.user_id != request.user.id and not _is_admin(request.user):
            return Response({
                'success': False,
                'error': "You can't delete this item"
            }, status=status.HTTP_403_FORBIDDEN)
        product.delete()
        return Response({
            'success': True,
            'message': 'Product deleted successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

