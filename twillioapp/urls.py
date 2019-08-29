from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import *

urlpatterns = [
                  path("", login_view, name="login"),
                  path("logout", logout_view, name="logout"),
                  path("send/message/", send_sms_mms, name="send_message"),
                  path("dashboard", dashboard, name="dashboard"),
                  path("update_sms", update_sms, name="update_sms"),
                  path("get_notifications", get_notifications, name="get_notifications"),
                  path("messaging", sms, name="messaging"),
                  path("message/success/<slug:sid>", sms, name="sms_success"),
                  path("message/failed/", sms, name="sms_failed"),
                  path("signup", registration_page, name="registration"),
                  path("signup/proceed/", sign_up_user, name="sign_up"),
                  path("reset_password/", reset_password_page, name="reset_password"),
                  path("reset_password/result/", reset_password_proceed, name="reset_password_proceed"),
                  path("reset_password/<slug:uidb64>/<slug:token>/<slug:query_payload>", reset_password,
                       name="reset_password_process"),
                  path("activate/<slug:uidb64>/<slug:token>", activate, name="activate"),
                  path("send_activation/<int:uid>", send_activation, name="send_activation"),
                  path("add_contact", add_contact, name="add_contact")
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
