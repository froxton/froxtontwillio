from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six

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
