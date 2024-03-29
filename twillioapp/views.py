from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.core.signing import TimestampSigner
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
from django.core import signing
from django.http import JsonResponse

from twilio.rest import Client
from twilio.twiml.messaging_response import *

from twillioapp.forms import RegistrationForm
from twillioapp.tasks import get_alphanumeric_countries
from twillioapp.utils import PasswordValidator, TokenGenerator, ResetPasswordTokenGenerator, user_activation
from .models import AuthenticationParameters, SentSms, MMSAttachment, UserAdditionalData, Contacts, \
    AlphaNumericCountries
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
        account_sid = auth_params.account_sid
        auth_token = auth_params.auth_token
        client = Client(account_sid, auth_token)
        try:
            request_domain_url = request.build_absolute_uri('/')[:-1]
            callback_url = f"{request_domain_url}/update_sms"
            country_code = request_data.get("country-code")
            receiver_number = request_data.get('to')
            receiver = f"{country_code}{receiver_number}" if not "+" in receiver_number else receiver_number

            if send_type == 'sms':
                from_num = request_data.get("from") or auth_params.phone_number
                message = client.messages.create(from_=from_num, body=request_data.get("body"),
                                                 to=receiver, status_callback=callback_url)
            else:
                file = request.FILES['mms_attachment']
                media_url = ''
                if file:
                    attach = MMSAttachment.objects.create(file=file)
                    media_url = f"{request_domain_url}/{attach.file.url}"
                from_num = request_data.get("from") or auth_params.phone_number
                message = client.messages.create(from_=from_num, body=request_data.get("body"),
                                                 to=request_data.get("to"), status_callback=callback_url,
                                                 media_url=media_url)
        except Exception as e:
            phone_numbers = list()
            contacts = Contacts.objects.filter(user=request.user)
            try:
                phone_numbers = [x.phone_number for x in client.incoming_phone_numbers.list()]
            except Exception:
                pass
            context = dict()
            context['phone_numbers'] = phone_numbers
            context['contacts'] = contacts
            context['error'] = str(e)
            context['countries'] = AlphaNumericCountries.objects.all().values()
            return render(request, 'sms.html', context)
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
                return HttpResponseRedirect(reverse("sms_success", args=(smsSent.sid,)))
            else:
                return HttpResponseRedirect(reverse("mms_success", args=(smsSent.sid,)))
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


@require_POST
def notify_received_sms(request):
    print(request.body)
    print(request.POST)
    print(request.GET)
    return HttpResponse("hello world")


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
            user = User.objects.filter(username=username).first()
            if not user.is_active:
                script = """$("#resend_activation").on('click', function () {
                            $.ajax({
                                type: "POST",
                                url: "%s",
                                success: function (data) {
                                   if (data.status == 'success'){
                                        let redirect_url = data.redirect_email;
                                        $('#activation').remove();
                                        $("#error").after(redirect_url);
                                   }
                                   else {
                                        let message = data.message;
                                        $('#activation').remove();
                                        $("#error").after(message);
                                   }
                                },
                            });
                        })""" % (reverse("send_activation", args=(user.id,)))
                return render(request, "login_view.html", {
                    "script": script,
                    "error": "Your account isn't activated, please visit your email and activate it, if you didn't receive activation link, click <span id='resend_activation'>resend activation</span>"})
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
    context = dict()

    if username:
        user = User.objects.filter(username=username)

    if email:
        user = User.objects.filter(email=email)

    if not user.exists():
        context = dict()
        context["errors"] = ["Couldn't find user with this username/email"]
        return render(request, "reset_password.html", context)

    user = user.first()

    if not user.is_active:
        script = """$("#resend_activation").on('click', function () {
            $.ajax({
                type: "POST",
                url: "%s",
                success: function (data) {
                   if (data.status == 'success'){
                        let redirect_url = data.redirect_email;
                        $('#activation').remove();
                        $("#error").after(redirect_url);
                   }
                   else {
                        let message = data.message;
                        $('#activation').remove();
                        $("#error").after(message);
                   }
                },
            });
        })""" % (reverse("send_activation", args=(user.id,)))
        return render(request, "reset_password.html", {
            "script": script,
            "user_id": user.id,
            "errors": ["Your account isn't activated, please visit your email and activate it, if you didn't receive activation link, click <span id='resend_activation'>resend activation</span>"]})

    account_activation_token = TokenGenerator()
    timestamp_signer = TimestampSigner()
    current_site = get_current_site(request)
    secret_data = {"user_id": user.id, "reset_access": True, "secret_word": "I Love Georgia"}
    signed_secret_data = timestamp_signer.sign(signing.dumps(secret_data)).replace(":", "-")
    mail_subject = 'Reset your Froxton account password.'
    message = render_to_string('acc_active_email.html', {
        'reset_check': True,
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "signed_secret_data": signed_secret_data
    })
    to_email = user.email or email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()
    email_domain = to_email.split("@")
    context["success"] = f"We sent reset password link in you email <a href='http://{email_domain[-1]}'>{to_email}</a><br><a href='/'>Back on page</a>"
    return render(request, "registration_view.html", context)


@require_http_methods(['GET', 'POST'])
def reset_password(request, uidb64, token, query_payload):
    account_activation_token = TokenGenerator()
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        signer = TimestampSigner()
        try:
            query_payload = query_payload.replace("-", ":")
            data = signer.unsign(query_payload, max_age=20)
        except Exception:
            return HttpResponse('Invalid activation payload')
        else:
            secret_data = signing.loads(data)
            uid = secret_data.get("user_id")
            reset_access = secret_data.get("reset_access")
            sec_word = secret_data.get("secret_word")

            if uid == user.id and reset_access is True and sec_word == "I Love Georgia":
                if request.method == 'GET':
                    query_payload = query_payload.replace(":", "-")
                    return render(request, "reset_password_page.html", {"uid": uidb64, "token": token, "query_payl": query_payload})
                else:
                    data = request.POST
                    password1 = data.get("password1")
                    password2 = data.get("password2")
                    errors = PasswordValidator(password1, password2).get_errors()

                    if len(errors) > 0:
                        return render(request, "reset_password_page.html",
                                      {"errors": errors, "uid": uidb64, "token": token, "query_payl": query_payload})

                    user.set_password(password1)
                    user.save()
                    auth_login(request, user)
                    return HttpResponseRedirect("/")
            else:
                return HttpResponse('Activation link is invalid!')
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

    email_domain = user_activation(request, user, email)
    context["success"] = f"We sent activation link in you email <a href='http://{email_domain[-1]}'>{email}</a><br><a href='/'>Back on page</a>"
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


@require_POST
@csrf_exempt
def send_activation(request, uid):
    try:
        user = User.objects.get(pk=uid)
    except Exception:
        return JsonResponse(data={'status': 'error', "message": "<h5 style=\"color: red;\" id='activation'>Invalid user</h5>"})
    else:
        email_domain = user_activation(request, user, user.email)
        return JsonResponse(data={'status': 'success', 'redirect_email': f"<h5 style=\"color: #199c61;\" id='activation'>Activation link has been sent to <a href='http://{email_domain[-1]}'>{user.email}</a></h5>"})


@require_POST
@csrf_exempt
def add_contact(request):
    data = request.POST
    user = request.user
    user_contacts = Contacts.objects.filter(user=user)

    contact_name = data.get("contactName")
    contact_number = data.get("contactNumber")
    contact_country = data.get("phoneCountry")

    number_exists = user_contacts.filter(contact_number__iexact=contact_number)

    if number_exists.exists():
        return JsonResponse(data={"status": "error", "message": f"This phone number is already saved as {number_exists.first().contact_name}"})

    Contacts.objects.create(
        user=user,
        contact_name=contact_name,
        contact_number=contact_number,
        contact_country_code=contact_country
    )
    return JsonResponse(data={"status": "success"})


@require_GET
def get_notifications(request):
    sms_notifications = SentSms.objects.filter(user=request.user).order_by("-update_date")
    data = json.loads(serializers.serialize("json", sms_notifications,
                                            fields=("status", "update_date", "from_num", "to", "have_seen", "sid"),
                                            use_natural_primary_keys=True))
    return JsonResponse(data, status=200, safe=False)


def sms(request, sid=None):
    auth_params = AuthenticationParameters.objects.filter(user=request.user).first()
    client = Client(auth_params.account_sid, auth_params.auth_token)
    phone_numbers = list()
    contacts = Contacts.objects.filter(user=request.user)
    countries = AlphaNumericCountries.objects.all().values()
    try:
        phone_numbers = [x.phone_number for x in client.incoming_phone_numbers.list()]
    except Exception:
        pass
    context = dict()
    context['phone_numbers'] = phone_numbers
    context['contacts'] = contacts
    context['countries'] = countries
    if len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "failed":
        context['error'] = "Invalid authentication parameters"
        return render(request, "sms.html", context)
    elif len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "success" and sid:
        context['success'] = f"Your message has been queued with SID: {sid}"
        return render(request, "sms.html", context)
    else:
        return render(request, "sms.html", context)


def mms(request, sid=None):
    auth_params = AuthenticationParameters.objects.filter(user=request.user).first()
    client = Client(auth_params.account_sid, auth_params.auth_token)
    phone_numbers = list()
    contacts = Contacts.objects.filter(user=request.user)
    countries = AlphaNumericCountries.objects.all().values()
    try:
        phone_numbers = [x.phone_number for x in client.incoming_phone_numbers.list()]
    except Exception:
        pass
    context = dict()
    context['phone_numbers'] = phone_numbers
    context['contacts'] = contacts
    context['countries'] = countries
    if len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "failed":
        context['error'] = "Invalid authentication parameters"
        return render(request, "mms.html", context)
    elif len(request.path.split("/")) >= 3 and request.path.split("/")[2] == "success" and sid:
        context['success'] = f"Your message has been queued with SID: {sid}"
        return render(request, "mms.html", context)
    else:
        return render(request, "mms.html", context)
