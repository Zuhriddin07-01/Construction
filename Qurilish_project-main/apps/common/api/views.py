from django.db.models import Avg, Count, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from apps.orders.models import Order
from ..models import WorkPhoto, WorkerReview
from .serializers import (
    WorkerListSerializer,
    WorkerDetailSerializer,
    WorkPhotoSerializer,
    ReviewSerializer,
)

User = get_user_model()


def _annotate_workers(queryset):
    """Har bir quruvchiga o'rtacha reyting va tugallangan buyurtmalar sonini qo'shadi."""
    return queryset.annotate(
        avg_rating=Avg('reviews_received__rating'),
        total_orders=Count(
            'assigned_orders',
            filter=Q(assigned_orders__status=Order.Status.DONE),
            distinct=True,
        ),
    )


class WorkerListView(generics.ListAPIView):
    """
    GET /api/common/workers/
    Barcha quruvchilar ro'yxati.
    ?search=Ali — ism bo'yicha qidirish
    ?address=Toshkent — shahar bo'yicha filter
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkerListSerializer

    def get_queryset(self):
        workers = _annotate_workers(User.objects.filter(role='builder', is_active=True))

        search = self.request.query_params.get('search')
        if search:
            workers = workers.filter(first_name__icontains=search) | \
                      workers.filter(last_name__icontains=search)

        address = self.request.query_params.get('address')
        if address:
            workers = workers.filter(address__icontains=address)

        return workers


class WorkerDetailView(generics.RetrieveAPIView):
    """
    GET /api/common/workers/{id}/
    Bitta quruvchining to'liq profili
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkerDetailSerializer
    queryset = User.objects.filter(role='builder')

    def get_queryset(self):
        return _annotate_workers(User.objects.filter(role='builder'))


class WorkPhotoUploadView(generics.CreateAPIView):
    """
    POST /api/common/photos/upload/
    Quruvchi o'z ish rasmini yuklaydi
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = WorkPhotoSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != 'builder':
            return Response(
                {'error': 'Faqat quruvchilar rasm yuklay oladi'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(worker=self.request.user)


class WorkerPhotosView(generics.ListAPIView):
    """
    GET /api/common/workers/{id}/photos/
    Quruvchining barcha ish rasmlari
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkPhotoSerializer

    def get_queryset(self):
        worker = get_object_or_404(User, pk=self.kwargs['pk'], role='builder')
        return WorkPhoto.objects.filter(worker=worker)


class ReviewListCreateView(APIView):
    """
    GET  /api/common/workers/{id}/reviews/ → Quruvchi sharhlari
    POST /api/common/workers/{id}/reviews/ → Sharh qoldirish (order_id majburiy)
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = ReviewSerializer

    def get(self, request, pk):
        worker = get_object_or_404(User, pk=pk, role='builder')
        reviews = WorkerReview.objects.filter(worker=worker)
        return Response({
            'worker_id': worker.id,
            'worker_name': worker.get_full_name(),
            'reviews': ReviewSerializer(reviews, many=True).data,
        })

    def post(self, request, pk):
        worker = get_object_or_404(User, pk=pk, role='builder')

        order_id = request.data.get('order')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not order_id or not rating:
            return Response(
                {'error': "Buyurtma (order) va baho (rating) kiritish shart"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return Response({'error': "Baho butun son bo'lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

        if rating not in range(1, 6):
            return Response(
                {'error': "Baho 1 dan 5 gacha bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = get_object_or_404(Order, pk=order_id)

        # Faqat shu buyurtma egasi (mijoz) va faqat tugallangan buyurtma uchun sharh qoldira oladi
        if order.client != request.user:
            return Response(
                {'error': "Faqat o'z buyurtmangizga sharh qoldira olasiz"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.builder != worker:
            return Response(
                {'error': "Bu buyurtma shu quruvchiga tegishli emas"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status != Order.Status.DONE:
            return Response(
                {'error': "Faqat tugallangan buyurtma uchun sharh qoldirish mumkin"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(order, 'review'):
            return Response(
                {'error': "Bu buyurtmaga sharh allaqachon qoldirilgan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review = WorkerReview.objects.create(
            order=order,
            worker=worker,
            client=request.user,
            rating=rating,
            comment=comment,
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
