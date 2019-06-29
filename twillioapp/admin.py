from django.contrib import admin
from .models import AuthenticationParameters, SentSms


class AuthParamsAdmin(admin.ModelAdmin):

    list_display = ["account_sid", "note", "auth_token", "user"]
    search_fields = ["account_sid", "note", "auth_token", "user__username"]


admin.site.register(AuthenticationParameters, AuthParamsAdmin)
admin.site.register(SentSms)
