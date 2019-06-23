from django.contrib.auth import authenticate
from django.http import HttpResponseRedirect
from django.shortcuts import render, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import auth_login, auth_logout
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.http import JsonResponse

from twilio.rest import Client

from .models import AuthenticationParameters, SentSms, MMSAttachment


@require_POST
def update_sms(request):
    data = request.POST
    sid = data.get("SmsSid")
    if sid:
        sms = SentSms.objects.filter(sid=sid.first())
        if sms:
            sms.status = data.get("SmsStatus")
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
        data = dict()
        try:
            account_sid = auth_params.account_sid
            auth_token = auth_params.auth_token
            client = Client(account_sid, auth_token)
            callback_url = f"{request.build_absolute_uri()}/update_sms"

            if send_type == 'sms':
                message = client.messages.create(from_=auth_params.phone_number, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url)
            else:
                file = request.FILES['mms_attachment']
                media_url = ''
                if file:
                    attach = MMSAttachment.objects.create(file=file)
                    media_url = attach.file.url
                message = client.messages.create(from_=auth_params.phone_number, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url,
                                                 media_url=media_url)
        except Exception as e:
            data["status"] = "error"
            data["message"] = str(e)
            return JsonResponse(data=data, status=402)
        else:
            SentSms.objects.create(
                user=user,
                account_sid=message.account_sid,
                sid=message.sid,
                from_num=message.from_,
                to=message.to,
                body=message.body,
                status=message.status
            )

            data["to"] = request_data.get("to")
            data["from"] = auth_params.phone_number
            data["body"] = request_data.get("body")
            data["date_created"] = message.date_created
            data["date_sent"] = message.date_sent
            data["sid"] = message.sid

            return JsonResponse(data=data, status=200)
    else:
        data = dict()
        data['status'] = 402
        data['status'] = "error"
        data['message'] = "Invalid authentication parameters for user"
        return JsonResponse(data=data, status=402)


@login_required(login_url="url")
@require_GET
def dashboard(request):
    return render(request, "dashboard.html")


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


def sms(request):
    return render(request, "sms.html")


def mms(request):
    return render(request, "mms.html")
