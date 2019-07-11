from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import auth_login, auth_logout
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.core import serializers
from django.http import JsonResponse

from twilio.rest import Client

from twillioapp.forms import RegistrationForm
from twillioapp.utils import PasswordValidator, TokenGenerator, ResetPasswordTokenGenerator
from .models import AuthenticationParameters, SentSms, MMSAttachment, UserAdditionalData
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
            request_domain_url = request.build_absolute_uri('/')[:-1]
            account_sid = auth_params.account_sid
            auth_token = auth_params.auth_token
            client = Client(account_sid, auth_token)
            callback_url = f"{request_domain_url}/update_sms"

            if send_type == 'sms':
                message = client.messages.create(from_=auth_params.phone_number, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url)
            else:
                file = request.FILES['mms_attachment']
                media_url = ''
                if file:
                    attach = MMSAttachment.objects.create(file=file)
                    media_url = f"{request_domain_url}/{attach.file.url}"
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
def registration_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return render(request, "registration_view.html")


@require_GET
def reset_password_page(request):
    if request.user.is_authenticated:
        pass
    else:
        return render(request, "reset_password.html")


@require_POST
def reset_password_proceed(request):
    data = request.POST
    username = data.get("username")
    email = data.get("email")
    user = None

    if username:
        user = User.objects.filter(username=username)

    if email:
        user = User.objects.filter(email=email)

    if not user.exists():
        context = dict()
        context["errors"] = ["Couldn't find user with this username/email"]
        return render(request, "reset_password.html", context)

    context = dict()
    user = user.first()
    account_activation_token = TokenGenerator()
    current_site = get_current_site(request)
    mail_subject = 'Activate your blog account.'
    message = render_to_string('acc_active_email.html', {
        'reset_check': True,
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    to_email = user.email or email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()
    email_domain = to_email.split("@")
    context["success"] = f"We sent reset password link in you email <a href='http://{email_domain[-1]}'>{to_email}</a>"
    return render(request, "registration_view.html", context)


@require_http_methods(['GET', 'POST'])
def reset_password(request,  uidb64, token):
    account_activation_token = TokenGenerator()
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        if request.method == 'GET':
            return render(request, "reset_password_page.html", {"uid": uidb64, "token": token})
        else:
            data = request.POST
            password1 = data.get("password1")
            password2 = data.get("password2")
            errors = PasswordValidator(password1, password2).get_errors()

            if len(errors) > 0:
                return render(request, "reset_password_page.html", {"errors": errors, "uid": uidb64, "token": token})

            user.set_password(password1)
            user.save()
            auth_login(request, user)
            return HttpResponseRedirect("/")
    else:
        return HttpResponse('Activation link is invalid!')


@require_POST
def sign_up_user(request):
    # TODO take all fields and validation in form
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    data = request.POST
    username = data.get("username")
    password1 = data.get("password1")
    password2 = data.get("password2")
    email = data.get("email")
    phone_number = data.get("phone_number")

    context = dict()
    errors = []

    if len(username) < 5:
        errors.append("Username must be equal or more than 5 symbols")
        context["errors"] = errors
        return render(request, "registration_view.html", context)

    user = User.objects.filter(Q(username=username) | Q(email=email)).exists()

    if user:
        errors.append("User with this email/username already exists")
        context["errors"] = errors
        return render(request, "registration_view.html", context)

    errors = PasswordValidator(password1, password2).get_errors()
    if len(errors) > 0:
        context["errors"] = errors
        return render(request, "registration_view.html", context)

    user = User.objects.create(
        username=username,
        email=email,
        is_active=False
    )
    user.set_password(password1)
    user.save()
    UserAdditionalData.objects.create(user=user, phone_number=phone_number)

    account_activation_token = TokenGenerator()
    current_site = get_current_site(request)
    mail_subject = 'Activate your blog account.'
    message = render_to_string('acc_active_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    to_email = email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()
    email_domain = to_email.split("@")
    context["success"] = f"We sent activation link in you email <a href='http://{email_domain[-1]}'>{to_email}</a>"
    return render(request, "registration_view.html", context)


def activate(request, uidb64, token):
    account_activation_token = TokenGenerator()
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth_login(request, user)
        return HttpResponseRedirect("/")
    else:
        return HttpResponse('Activation link is invalid!')


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
