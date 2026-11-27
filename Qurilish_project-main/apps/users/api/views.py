from django.contrib.auth import logout, update_session_auth_hash
from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, authenticate
from rest_framework.authtoken.models import Token
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    AvatarSerializer,
)
 
User = get_user_model()

AuthUser = inline_serializer('AuthUser', fields={
    'id': serializers.IntegerField(), 'username': serializers.CharField(),
    'full_name': serializers.CharField(), 'role': serializers.CharField(),
})
AuthResponse = inline_serializer('AuthResponse', fields={
    'message': serializers.CharField(), 'token': serializers.CharField(), 'user': AuthUser,
})
MessageResponse = inline_serializer('MessageResponse', fields={'message': serializers.CharField()})
 
 
class RegisterView(APIView):
    """
    POST /api/users/register/
    Yangi foydalanuvchi ro'yxatdan o'tishi
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    @extend_schema(responses={201: AuthResponse})
    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'message': 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz!',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'role': user.role,
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class LoginView(APIView):
    """
    POST /api/users/login/
    Tizimga kirish — token qaytaradi
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
 
    @extend_schema(responses=AuthResponse)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
 
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'message': 'Tizimga muvaffaqiyatli kirdingiz!',
                    'token': token.key,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.get_full_name(),
                        'role': user.role,
                    }
                })
            return Response(
                {'error': 'Username yoki parol noto\'g\'ri!'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class LogoutView(APIView):
    """
    POST /api/users/logout/
    Tizimdan chiqish — tokenni o'chiradi
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
 
    @extend_schema(request=None, responses=MessageResponse)
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({'message': 'Tizimdan chiqdingiz!'})
 
 
class ProfileView(APIView):
    """
    GET   /api/users/profile/  → Profilni ko'rish
    PATCH /api/users/profile/  → Profilni yangilash
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
 
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
 
    @extend_schema(responses=inline_serializer('ProfileUpdate', fields={
        'message': serializers.CharField(), 'user': UserProfileSerializer(),
    }))
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profil yangilandi!', 'user': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class ChangePasswordView(APIView):
    """
    POST /api/users/change-password/
    Parol o'zgartirish
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
 
    @extend_schema(responses=MessageResponse)
    @transaction.atomic
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
 
            # Eski parolni tekshirish
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'error': 'Eski parol noto\'g\'ri!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
 
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            Token.objects.filter(user=user).delete()
            update_session_auth_hash(request, user)
            return Response({'message': 'Parol muvaffaqiyatli o\'zgartirildi!'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class AvatarUploadView(APIView):
    """
    POST /api/users/avatar/
    Profil rasmini yuklash
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = AvatarSerializer

    @extend_schema(responses=MessageResponse)
    def post(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Profil rasmi yangilandi!'})
