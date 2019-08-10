from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMessage
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
import requests
import bs4


class PasswordValidator:

    def __init__(self, password, password2):
        self.password = password
        self.password2 = password2
        self._matched = True
        self._errors = []
        self._start_validation()

    def _start_validation(self):
        self.check_password_exact()
        self.check_numbers()
        self.check_symbols()

    def check_password_exact(self):
        if self.password != self.password2:
            self._matched = False
            self._errors.append("Repeated password didn't match")

    def check_symbols(self):
        self._contains_str(self.password, r"\"!# $%&'()*+,-./:;<=>?@[\]^_`{|}~",
                           "One or more special symbol is required")

    def check_numbers(self):
        self._contains_str(self.password, "0123456789", "One or more number is required")

    def _contains_str(self, pattern, char_array, error_message):
        if self._matched:
            contains = False
            for k in pattern:
                if k in char_array:
                    contains = True
                    break
            if not contains:
                self._errors.append(error_message)

    def get_errors(self):
        return self._errors


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.is_active)
        )


class ResetPasswordTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.email)
        )


def user_activation(request, user, email):
    account_activation_token = TokenGenerator()
    current_site = get_current_site(request)
    mail_subject = 'Activate your Froxton account.'
    message = render_to_string('acc_active_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    to_email = email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()
    email_domain = to_email.split("@")
    return email_domain



