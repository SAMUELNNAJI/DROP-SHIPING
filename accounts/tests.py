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

    def test_wrong_password_renders_signin_with_error(self):
        """Bad credentials must re-render the page (HTTP 200) with the
        error message — never a 500 — so the VPS login page stays usable."""
        response = self.client.post(reverse('signin'), {
            'username': self.admin.username,
            'password': 'definitely-wrong',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')
        # The field accepts a username or an email — the label must say so.
        self.assertContains(response, 'Email or username')

    def test_exact_username_beats_case_insensitive_duplicate(self):
        """Two accounts whose usernames differ only by case must not collide.

        A blind case-insensitive lookup resolves 'Samuel' to the lower-pk
        'samuel' row and rejects the correct password — the exact symptom of
        "works in /admin/, wrong password on /signin/".
        """
        User.objects.create_user(
            username='samuel', email='sam.lower@example.com', password='LowerPass123!'
        )
        User.objects.create_user(
            username='Samuel', email='sam.upper@example.com', password='UpperPass123!'
        )

        response = self.client.post(reverse('signin'), {
            'username': 'Samuel',
            'password': 'UpperPass123!',
        })
        self.assertRedirects(
            response, reverse('dashboard_buyer'), fetch_redirect_response=False
        )

        # The case-variant account still signs in with its own password.
        self.client.logout()
        response = self.client.post(reverse('signin'), {
            'username': 'samuel',
            'password': 'LowerPass123!',
        })
        self.assertRedirects(
            response, reverse('dashboard_buyer'), fetch_redirect_response=False
        )


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

