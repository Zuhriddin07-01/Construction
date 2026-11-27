from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_public_registration_rejects_admin_role(self):
        response = self.client.post('/api/users/register/', {
            'username': 'demo', 'role': 'admin',
            'password': 'demo-pass-Unique-331', 'password2': 'demo-pass-Unique-331',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='demo').exists())

    def test_avatar_must_be_an_image(self):
        user = get_user_model().objects.create_user(username='demo')
        self.client.force_authenticate(user)
        upload = SimpleUploadedFile('example.txt', b'demo', content_type='text/plain')
        response = self.client.post('/api/users/avatar/', {'avatar': upload}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_password_change_revokes_token(self):
        user = get_user_model().objects.create_user(username='demo', password='old-pass-134')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.post('/api/users/change-password/', {
            'old_password': 'old-pass-134',
            'new_password': 'brand-new-pass-827', 'new_password2': 'brand-new-pass-827',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/users/profile/').status_code, 401)
