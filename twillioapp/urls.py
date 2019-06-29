from django.urls import path
from .views import *

urlpatterns = [
    path("", login_view, name="login"),
    path("send/sms/", send_sms_mms, name="send_sms"),
    path("send/mms/", send_sms_mms, name="send_mms"),
    path("dashboard", dashboard, name="dashboard"),
    path("update_sms", update_sms, name="update_sms"),
    path("get_notifications", get_notifications, name="get_notifications"),
    path("sms", sms, name="sms"),
    path("mms", mms, name="mms")
]