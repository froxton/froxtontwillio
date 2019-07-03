from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import *

urlpatterns = [
    path("", login_view, name="login"),
    path("logout", logout_view, name="logout"),
    path("send/sms/", send_sms_mms, name="send_sms"),
    path("send/mms/", send_sms_mms, name="send_mms"),
    path("dashboard", dashboard, name="dashboard"),
    path("update_sms", update_sms, name="update_sms"),
    path("get_notifications", get_notifications, name="get_notifications"),
    path("sms", sms, name="sms"),
    path("sms/success/<slug:sid>", sms, name="sms_success"),
    path("sms/failed/", sms, name="sms_failed"),
    path("mms", mms, name="mms")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)