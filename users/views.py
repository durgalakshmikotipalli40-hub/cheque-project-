from django.shortcuts import render, redirect
from .forms import RegistrationForm, ImageUploadForm
from .models import UserAccount
import os
from django.conf import settings
import numpy as np
import cv2
#import matplotlib
#matplotlib.use("Agg")
#import matplotlib.pyplot as plt

from django.core.mail import send_mail
import random
from django.utils import timezone
from datetime import timedelta
from PIL import Image
from django.contrib import messages

from .utils.final_pipeline import process_cheque
from .utils.gemini_extract import extract_cheque_details
from .utils.gemini_validate import validate_cheque_image


# ===========================
# OTP GENERATOR
# ===========================
def generate_otp():
    return str(random.randint(100000, 999999))


# ===========================
# SEND OTP TO OWNER
# ===========================
def send_owner_alert(request, account_number):

    email = "durgalakshmikotipalli40@gmail.com"

    if not email:
        return False

    otp = generate_otp()
    request.session['owner_otp'] = otp

    try:
        send_mail(
            subject="Cheque Verification OTP",
            message=f"Your OTP is: {otp}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
        return True
    except Exception:
        return False
# resend otp #

def resend_otp(request):
    user_id = request.session.get('verify_user')

    if not user_id:
        messages.error(request, "Session expired")
        return redirect('register')

    user = UserAccount.objects.get(id=user_id)

    otp = generate_otp()
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.save()

    send_mail(
        'Resend OTP',
        f'Your new OTP is: {otp}',
        settings.EMAIL_HOST_USER,
        [user.email],
    )

    messages.success(request, "New OTP sent to your email")
    return redirect('verify_otp')

# ===========================
# BASE
# ===========================
def basefunction(request):
    return render(request, 'base.html')


# ===========================
# REGISTER
# ===========================
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            if UserAccount.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect('register')

            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])

            otp = generate_otp()
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.status = 'waiting'
            user.save()

            request.session['verify_user'] = user.id

            send_mail(
                'OTP Verification',
                f'Your OTP is: {otp}',
                settings.EMAIL_HOST_USER,
                [user.email],
            )

            return redirect('verify_otp')

    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


# ===========================
# VERIFY OTP
# ===========================
def verify_otp(request):
    user_id = request.session.get('verify_user')

    if not user_id:
        return redirect('register')

    user = UserAccount.objects.get(id=user_id)

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        if user.otp_created_at and timezone.now() > user.otp_created_at + timedelta(minutes=5):
            messages.error(request, "OTP expired")
            return redirect('verify_otp')

        if entered_otp == str(user.otp):
            user.status = 'activated'
            user.otp = None
            user.save()

            request.session.flush()
            return redirect('userlogin')
        else:
            messages.error(request, "Invalid OTP")

    return render(request, 'verify_otp.html')


# ===========================
# LOGIN
# ===========================
def userlogin(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = UserAccount.objects.get(username=username)

            if not user.check_password(password):
                messages.error(request, "Incorrect password")

            elif user.status == 'waiting':
                messages.warning(request, "Verify email first")

            elif user.status == 'blocked':
                messages.error(request, "Account blocked")

            else:
                request.session['user_id'] = user.id
                return redirect('userhome')

        except UserAccount.DoesNotExist:
            messages.error(request, "User not found")

    return render(request, 'userlogin.html')


# ===========================
# USER HOME
# ===========================
def userhome(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('userlogin')

    user = UserAccount.objects.get(id=user_id)
    return render(request, 'userhome.html', {'user': user})


# ===========================
# LOGOUT
# ===========================
def logout_view(request):
    request.session.flush()
    return redirect('userlogin')


# ===========================
# PREDICTION
# ===========================
def prediction(request):

    uploaded_image = None
    output = None
    details = None
    error = None

    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)

        if form.is_valid():
            img_file = form.cleaned_data.get('image')

            if not img_file:
                return render(request, 'prediction.html', {
                    'form': form,
                    'error': "Upload image"
                })

            save_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")
            os.makedirs(save_dir, exist_ok=True)

            img_name = img_file.name
            ext = img_name.split('.')[-1].lower()

            if ext in ["tif", "tiff"]:
                img = Image.open(img_file).convert("RGB")
                img_name = img_name.rsplit('.', 1)[0] + ".jpg"
                save_path = os.path.join(save_dir, img_name)
                img.save(save_path, "JPEG")
            else:
                save_path = os.path.join(save_dir, img_name)
                with open(save_path, "wb+") as f:
                    for chunk in img_file.chunks():
                        f.write(chunk)

            # ✅ FILE SAVE CHECK
            if not os.path.exists(save_path):
                return render(request, 'prediction.html', {
                    'form': form,
                    'error': "File save failed"
                })

            uploaded_image = f"{settings.MEDIA_URL}uploaded/{img_name}"

            # ================= GEMINI VALIDATION =================
            try:
                if not request.session.get('validated'):
                    is_cheque, reason = validate_cheque_image(save_path)
                    if is_cheque:
                        request.session['validated'] = True
                else:
                    is_cheque = True
                    reason = "Already validated"
            except:
                is_cheque = True

            if not is_cheque:
                return render(request, 'prediction.html', {
                    'form': form,
                    'error': "Invalid Document",
                    'uploaded_image': uploaded_image
                })

            # ================= PROCESS =================
            output = process_cheque(save_path)
            details = extract_cheque_details(save_path)

            # ✅ SESSION FIX
            request.session['uploaded_image'] = uploaded_image
            request.session['output'] = output
            request.session['details'] = details

            # ================= OTP =================
            if details:
                acc = details.get("Account Number") or details.get("account_number")

                if acc:
                    sent = send_owner_alert(request, acc)

                    if sent:
                        return redirect('verify_owner_otp')

        else:
            error = "Invalid form"

    else:
        form = ImageUploadForm()

    return render(request, 'prediction.html', {
        'form': form,
        'uploaded_image': uploaded_image,
        'output': output,
        'details': details,
        'error': error
    })


# ===========================
# VERIFY OWNER OTP
# ===========================
def verify_owner_otp(request):

    if request.method == "POST":
        entered = request.POST.get("otp")
        real = request.session.get("owner_otp")

        if entered == real:

            uploaded_image = request.session.get("uploaded_image")
            output = request.session.get("output")
            details = request.session.get("details")

            request.session.flush()

            return render(request, "prediction.html", {
                "uploaded_image": uploaded_image,
                "output": output,
                "details": details,
                "success": "Cheque Verified"
            })

        else:
            return render(request, "verify_owner_otp.html", {
                "error": "Invalid OTP"
            })

    return render(request, "verify_owner_otp.html")