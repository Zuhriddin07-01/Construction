from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Product, ProductComment, ProductRating  # ← import
from .serializers import (                                   # ← import
    ProductSerializer,
    ProductCommentSerializer,
    ProductRatingSerializer,
    ProductImageSerializer,
)

# keyin viewlar ...
 
 
class ProductListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/products/  → Barcha xizmatlar ro'yxati
    POST /api/products/  → Yangi xizmat yaratish (faqat quruvchi)
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
 
    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('builder').prefetch_related(
            'images', 'comments__user', 'ratings',
        )
 
    def perform_create(self, serializer):
        if self.request.user.role != 'builder':
            raise PermissionDenied('Faqat quruvchilar xizmat qo‘sha oladi.')
        serializer.save(builder=self.request.user)
 
 
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/products/{id}/  → Bitta xizmat
    PATCH  /api/products/{id}/  → Yangilash (faqat egasi)
    DELETE /api/products/{id}/  → O'chirish (faqat egasi)
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        products = Product.objects.select_related('builder').prefetch_related(
            'images', 'comments__user', 'ratings',
        )
        if self.request.user.is_authenticated:
            return products.filter(Q(is_active=True) | Q(builder=self.request.user))
        return products.filter(is_active=True)
 
    def update(self, request, *args, **kwargs):
        product = self.get_object()
        if product.builder != request.user:
            return Response({'error': 'Siz bu xizmatni o\'zgartira olmaysiz'}, status=403)
        return super().update(request, *args, **kwargs)
 
    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.builder != request.user:
            return Response({'error': 'Siz bu xizmatni o\'chira olmaysiz'}, status=403)
        return super().destroy(request, *args, **kwargs)
 
 
class ProductCommentView(generics.CreateAPIView):
    """
    POST /api/products/{id}/comment/  → Savol yoki sharh qoldirish
    """
    serializer_class = ProductCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs['pk'], is_active=True)
        serializer.save(user=self.request.user, product=product)
 
 
class ProductRatingView(APIView):
    """
    POST /api/products/{id}/rate/  → Baholash (1-5)
    """
    permission_classes = [permissions.IsAuthenticated]
 
    @extend_schema(request=ProductRatingSerializer, responses=inline_serializer(
        'ProductRatingResult', fields={'message': serializers.CharField(), 'rating': serializers.IntegerField()},
    ))
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)
        serializer = ProductRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating_value = serializer.validated_data['rating']
        _, created = ProductRating.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating_value}
        )
        msg = 'Baho qo\'yildi' if created else 'Baho yangilandi'
        return Response({'message': msg, 'rating': rating_value})
 
 
class ProductImageUploadView(generics.CreateAPIView):
    """
    POST /api/products/{id}/images/  → Rasm yuklash
    """
    serializer_class = ProductImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]
 
    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs['pk'], is_active=True)
        if product.builder != self.request.user:
            raise PermissionDenied('Siz bu xizmatga rasm yuklay olmaysiz')
        serializer.save(product=product)

# Create your views here.
