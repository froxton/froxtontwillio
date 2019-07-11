from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from twillioapp.utils import PasswordValidator


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=32)
    password1 = forms.CharField(max_length=32)
    password2 = forms.CharField(max_length=32)
    email = forms.EmailField(max_length=64)
    phone_number = forms.CharField(max_length=16)

    def clean_username(self):
        user = User.objects.filter(username=self.cleaned_data.get("username"))
        if user.exists():
            self.errors.append(ValidationError("User with this username already exists"))
        return self.cleaned_data.get("username")

    def clean_email(self):
        user = User.objects.filter(username=self.cleaned_data.get("email"))
        if user.exists():
            self.errors.append(ValidationError("User with this email already exists"))
        return self.cleaned_data.get("email")

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        self.errors.extend(PasswordValidator(password1, password2).get_errors())
        return self.cleaned_data.get("password1")





