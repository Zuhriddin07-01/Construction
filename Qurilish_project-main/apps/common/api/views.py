from drf_spectacular.utils import OpenApiParameter, extend_schema
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
    ReviewInputSerializer,
    WorkerReviewsSerializer,
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

    @extend_schema(parameters=[
        OpenApiParameter('search', str, description='Builder first or last name'),
    ])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        workers = _annotate_workers(User.objects.filter(role='builder', is_active=True))

        search = self.request.query_params.get('search')
        if search:
            workers = workers.filter(first_name__icontains=search) | \
                      workers.filter(last_name__icontains=search)

        return workers.order_by('pk')


class WorkerDetailView(generics.RetrieveAPIView):
    """
    GET /api/common/workers/{id}/
    Bitta quruvchining to'liq profili
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkerDetailSerializer
    queryset = User.objects.filter(role='builder', is_active=True)

    def get_queryset(self):
        return _annotate_workers(User.objects.filter(role='builder', is_active=True))


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
    queryset = WorkPhoto.objects.none()
    """
    GET /api/common/workers/{id}/photos/
    Quruvchining barcha ish rasmlari
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkPhotoSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset
        worker = get_object_or_404(User, pk=self.kwargs['pk'], role='builder', is_active=True)
        return WorkPhoto.objects.filter(worker=worker)


class ReviewListCreateView(APIView):
    """
    GET  /api/common/workers/{id}/reviews/ → Quruvchi sharhlari
    POST /api/common/workers/{id}/reviews/ → Sharh qoldirish (order_id majburiy)
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = ReviewSerializer

    @extend_schema(responses=WorkerReviewsSerializer)
    def get(self, request, pk):
        worker = get_object_or_404(User, pk=pk, role='builder', is_active=True)
        reviews = WorkerReview.objects.filter(worker=worker)
        return Response({
            'worker_id': worker.id,
            'worker_name': worker.get_full_name(),
            'reviews': ReviewSerializer(reviews, many=True).data,
        })

    @extend_schema(request=ReviewInputSerializer, responses={201: ReviewSerializer})
    def post(self, request, pk):
        worker = get_object_or_404(User, pk=pk, role='builder', is_active=True)

        serializer = ReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = get_object_or_404(Order, pk=data['order'], client=request.user)

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
        review, created = WorkerReview.objects.get_or_create(
            order=order,
            defaults={'worker': worker, 'client': request.user,
                      'rating': data['rating'], 'comment': data['comment']},
        )
        if not created:
            return Response(
                {'error': "Bu buyurtmaga sharh allaqachon qoldirilgan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
