from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer, OrderStatusSerializer


class VisibleOrders:
    queryset = Order.objects.select_related('client', 'builder')
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        if user.role == 'client':
            return self.queryset.filter(client=user)
        if user.role == 'builder':
            return self.queryset.filter(
                Q(builder=user) | Q(builder__isnull=True, status=Order.Status.PENDING)
            )
        return self.queryset.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['viewer_id'] = self.request.user.pk
        return context


class OrderListCreateView(VisibleOrders, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        if self.request.user.role != 'client':
            raise PermissionDenied('Faqat mijozlar buyurtma bera oladi.')
        serializer.save(client=self.request.user)


class OrderDetailView(VisibleOrders, generics.RetrieveAPIView):
    @extend_schema(request=OrderStatusSerializer, responses=OrderSerializer)
    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        user = request.user

        if user.role != 'builder':
            raise PermissionDenied('Faqat quruvchilar holatni yangilay oladi.')
        allowed = {
            Order.Status.PENDING: {Order.Status.ACCEPTED, Order.Status.REJECTED},
            Order.Status.ACCEPTED: {Order.Status.IN_WORK, Order.Status.REJECTED},
            Order.Status.IN_WORK: {Order.Status.DONE},
        }
        if new_status not in allowed.get(order.status, set()):
            raise ValidationError({'status': 'Bu holatga o‘tish mumkin emas.'})
        if new_status in (Order.Status.IN_WORK, Order.Status.DONE) and order.builder_id != user.pk:
            raise PermissionDenied('Bu amalni biriktirilgan quruvchi bajarishi mumkin.')

        builder_id = user.pk if new_status == Order.Status.ACCEPTED else order.builder_id
        updated = Order.objects.filter(
            pk=order.pk, status=order.status, builder_id=order.builder_id,
        ).update(status=new_status, builder_id=builder_id, updated_at=timezone.now())
        if not updated:
            return Response({'detail': 'Order changed. Reload it and try again.'}, status=status.HTTP_409_CONFLICT)

        order.refresh_from_db()
        return Response(self.get_serializer(order).data)
