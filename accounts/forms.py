from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class ErrorClassMixin:
    """Adds an `is-error` class to widgets whose field failed validation.

    Runs after `full_clean()` so the templates can style invalid inputs in
    red (`.auth-input.is-error`) without any template-level plumbing.
    """

    def full_clean(self):
        super().full_clean()
        for name, field in self.fields.items():
            if self._errors and self._errors.get(name):
                classes = field.widget.attrs.get('class', '')
                if 'is-error' not in classes:
                    field.widget.attrs['class'] = (classes + ' is-error').strip()


class SignUpForm(ErrorClassMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'auth-input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        label='I am joining as',
        # rendered as two selectable pills on the signup page
        widget=forms.RadioSelect(),
        initial='buyer',
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Phone',
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': '+1 234 567 8900',
            'autocomplete': 'tel',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Choose a username',
            'email': 'you@example.com',
            'phone': '+1 234 567 8900',
        }
        autocomplete = {
            'username': 'username',
            'email': 'email',
            'password1': 'new-password',
            'password2': 'new-password',
        }
        for name in ('username', 'email', 'password1', 'password2'):
            field = self.fields[name]
            field.widget.attrs['class'] = 'auth-input'
            if name in placeholders:
                field.widget.attrs['placeholder'] = placeholders[name]
            if name in autocomplete:
                field.widget.attrs['autocomplete'] = autocomplete[name]
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        self.fields['username'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Try signing in instead.')
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken — please pick another one.')
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        # keep digits, spaces, +, -, ( and )
        cleaned = ''.join(ch for ch in phone if ch.isdigit() or ch in '+ -()')
        if phone and len(cleaned.replace(' ', '')) < 7:
            raise forms.ValidationError('Enter a valid phone number, e.g. +1 234 567 8900.')
        return cleaned


class SignInForm(ErrorClassMixin, AuthenticationForm):
    username = forms.CharField(label='Username or email', widget=forms.TextInput(attrs={
        'class': 'auth-input',
        'placeholder': 'Username or email',
        'autocomplete': 'username',
    }))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'class': 'auth-input',
        'placeholder': 'Enter your password',
        'autocomplete': 'current-password',
    }))

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            return username

        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            user = User.objects.filter(email__iexact=username).first()
        return user.username if user else username
