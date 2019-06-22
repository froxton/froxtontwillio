from django.db import models
from django.contrib.auth.models import User
from .utils import random_password_generator


class AuthenticationParameters(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_sid = models.CharField(max_length=256, blank=False, null=False)
    auth_token = models.CharField(max_length=256, blank=False, null=False)
    phone_number = models.CharField(max_length=65, blank=False, null=False)
    sms_password = models.CharField(max_length=32, blank=False, null=False, editable=False)
    rand_identificator = models.CharField(max_length=32, blank=False, null=False, editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sms_password and not self.rand_identificator:
            self.sms_password = random_password_generator()
            self.rand_identificator = random_password_generator()
        super(AuthenticationParameters, self).save(*args, **kwargs)

    def __str__(self):
        return self.account_sid

    class Meta:
        db_table = "twilio_auth_params"


class SentSms(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    account_sid = models.CharField(max_length=256, blank=False, null=False)
    sid = models.CharField(max_length=256, blank=False, null=False, primary_key=True)
    from_num = models.CharField(max_length=32, blank=False, null=False)
    to = models.CharField(max_length=32, blank=False, null=False)
    body = models.CharField(max_length=4096, blank=False, null=False)
    status = models.CharField(max_length=16, blank=False, null=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sid

    class Meta:
        db_table = "twilio_sms_data"


class MMSAttachment(models.Model):
    account_sid = models.CharField(max_length=256, blank=False, null=False)
    file = models.FileField(upload_to="mms_attachments")
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.account_sid

