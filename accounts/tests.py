from django.test import TestCase
from django.urls import reverse

from .models import User


class SignInRedirectTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin-test',
            email='admin@example.com',
            password='TestPass123!',
        )

    def test_superuser_can_sign_in_with_email_and_open_admin_dashboard(self):
        response = self.client.post(reverse('signin'), {
            'username': self.admin.email,
            'password': 'TestPass123!',
        })

        self.assertRedirects(response, reverse('dashboard_admin'))
        dashboard = self.client.get(reverse('dashboard_admin'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Admin workspace')

    def test_signin_honors_safe_next_url(self):
        response = self.client.post(
            reverse('signin') + '?next=/dashboards/admin/',
            {
                'username': self.admin.username,
                'password': 'TestPass123!',
            },
        )

        self.assertRedirects(response, '/dashboards/admin/')


class SignOutTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin-test',
            email='admin@example.com',
            password='TestPass123!',
        )

    def test_signout_preserves_superuser_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('signout'))

        self.assertRedirects(response, reverse('home'))
        admin = User.objects.get(pk=self.admin.pk)
        self.assertTrue(admin.is_active)

        response = self.client.post(reverse('signin'), {
            'username': self.admin.username,
            'password': 'TestPass123!',
        })
        self.assertRedirects(response, reverse('dashboard_admin'))

