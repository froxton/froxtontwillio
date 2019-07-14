from django.db import models
from django.contrib.auth.models import User


class UserAdditionalData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=16, blank=True, null=True)

    def __str__(self):
        return self.user.username

    class Meta:
        db_table = "twilio_auth_user_ext_data"


class Contacts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contact_name = models.CharField(max_length=256, blank=False, null=False)
    contact_number = models.CharField(max_length=32, blank=False, null=False)
    contact_country = models.CharField(max_length=32, blank=False, null=False)

    def __str__(self):
        return f"{self.contact_name} - {self.contact_number}"

    class Meta:
        db_table = 'user_contacts'


class AuthenticationParameters(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_sid = models.CharField(max_length=256, blank=False, null=False)
    auth_token = models.CharField(max_length=256, blank=False, null=False)
    phone_number = models.CharField(max_length=65, blank=False, null=False)
    note = models.CharField(max_length=256, blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

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
    have_seen = models.BooleanField(default=False)
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

