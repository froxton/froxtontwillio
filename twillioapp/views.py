from django.contrib.auth import authenticate
from django.http import HttpResponseRedirect
from django.shortcuts import render, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import auth_login, auth_logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.core import serializers
from django.http import JsonResponse

from twilio.rest import Client

from .models import AuthenticationParameters, SentSms, MMSAttachment
import json


@csrf_exempt
@require_POST
def update_sms(request):
    data = request.POST
    sid = data.get("SmsSid")
    if sid:
        sms = SentSms.objects.filter(sid=sid).first()
        if sms:
            sms.status = data.get("SmsStatus")
            sms.have_seen = False
            sms.save()
            return JsonResponse(data={"status": "OK"}, status=200)
        else:
            return JsonResponse(data={"status": "ERROR - SMS NOT FOUND"}, status=402)
    else:
        return JsonResponse(data={"status": "ERROR - SID IS MISSING"}, status=402)


@login_required(login_url="login")
@require_POST
def send_sms_mms(request):
    user = request.user
    request_data = request.POST
    auth_params = AuthenticationParameters.objects.filter(user=user).first()

    send_type = request_data.get("send_type")
    if auth_params:
        try:
            account_sid = auth_params.account_sid
            auth_token = auth_params.auth_token
            client = Client(account_sid, auth_token)
            callback_url = f"{request.build_absolute_uri()}update_sms"

            if send_type == 'sms':
                message = client.messages.create(from_=auth_params.phone_number, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url)
            else:
                file = request.FILES['mms_attachment']
                media_url = ''
                if file:
                    attach = MMSAttachment.objects.create(file=file)
                    media_url = f"{request.build_absolute_uri('/')[:-1]}{attach.file.url}"
                message = client.messages.create(from_=auth_params.phone_number, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url,
                                                 media_url=media_url)
        except Exception as e:
            if send_type == "sms":
                return render(request, 'sms.html', {"error": str(e)})
            else:
                return render(request, 'mms.html', {"error": str(e)})
        else:
            smsSent = SentSms.objects.create(
                user=user,
                account_sid=message.account_sid,
                sid=message.sid,
                from_num=message.from_,
                to=message.to,
                body=message.body,
                status=message.status,
                have_seen=True
            )

            if send_type == "sms":
                return HttpResponseRedirect(reverse("sms_success", args=(smsSent.sid, )))
            else:
                return render(request, 'mms.html', {"success": f"Your message has been queued with SID: {message.sid}"})
    else:
        if send_type == "sms":
            return HttpResponseRedirect(reverse("sms_failed"))
        else:
            return render(request, 'mms.html', {"success": f"Invalid authentication parameters"})


@login_required(login_url="url")
@require_GET
def dashboard(request):
    return render(request, "dashboard.html")


def logout_view(request):
    auth_logout(request)
    return HttpResponseRedirect("/")


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse("dashboard"))
        return render(request, 'login_view.html')
    else:
        data = request.POST
        username = data.get("username")
        password = data.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return HttpResponseRedirect(reverse("dashboard"))
        else:
            return render(request, "login_view.html", {"error": "Username or password is incorrect"})


@require_GET
def get_notifications(request):
    sms_notifications = SentSms.objects.filter(user=request.user).order_by("-update_date")
    data = json.loads(serializers.serialize("json", sms_notifications,
                                            fields=("status", "update_date", "from_num", "to", "have_seen", "sid"),
                                            use_natural_primary_keys=True))
    return JsonResponse(data, status=200, safe=False)


def sms(request, sid=None):
    if len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "failed":
        return render(request, "sms.html", {"error": f"Invalid authentication parameters"})
    elif len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "success" and sid:
        return render(request, "sms.html", {"success": f"Your message has been queued with SID: {sid}"})
    else:
        return render(request, "sms.html")


def mms(request, sid=None):
    if len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "failed":
        return render(request, "mms.html", {"error": f"Invalid authentication parameters"})
    elif len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "success" and sid:
        return render(request, "mms.html", {"success": f"Your message has been queued with SID: {sid}"})
    else:
        return render(request, "mms.html")
