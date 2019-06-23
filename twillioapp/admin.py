from django.contrib import admin
from .models import AuthenticationParameters, SentSms

admin.site.register(AuthenticationParameters)
admin.site.register(SentSms)
