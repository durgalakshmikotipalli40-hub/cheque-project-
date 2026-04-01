from django.shortcuts import render, redirect
from .forms import RegistrationForm, ImageUploadForm
from .models import UserAccount
import os
from django.conf import settings
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
    except Exception as e:
        print("OWNER OTP ERROR:", e)
        return False


# ===========================
# BASE
# ===========================
def basefunction(request):
    return render(request, 'base.html')


# ===========================
# REGISTER
# ===========================
# ===========================
# REGISTER
# ===========================
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data['email']

            # ✅ EMAIL ALREADY EXISTS CHECK
            if UserAccount.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return render(request, 'register.html', {'form': form})

            # ✅ PASSWORD VALIDATION ADD HERE
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['confirm_password']

            if password != confirm_password:
                messages.error(request, "Passwords do not match")
                return render(request, 'register.html', {'form': form})

            user = form.save(commit=False)

            # ✅ SET PASSWORD
            user.set_password(password)

            # ✅ OTP GENERATION
            otp = generate_otp()
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.status = 'waiting'
            user.save()

            request.session['verify_user'] = user.id

            # ✅ SAFE EMAIL SEND
            try:
                send_mail(
                    'OTP Verification',
                    f'Your OTP is: {otp}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                )
            except Exception as e:
                print("EMAIL ERROR:", e)
                messages.error(request, "Failed to send OTP")
                return render(request, 'register.html', {'form': form})
            
        else:
            messages.error(request, "Invalid form data")
    

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

    user = UserAccount.objects.filter(id=user_id).first()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        if entered_otp == str(user.otp):
            user.status = 'activated'
            user.otp = None
            user.save()

            request.session.flush()
            return redirect('userlogin')

        else:
            messages.error(request, "Invalid OTP")

    return render(request, 'verify_otp.html')

#resend otp 

def resend_otp(request):
    user_id = request.session.get('verify_user')

    if not user_id:
        messages.error(request, "Session expired")
        return redirect('register')

    user = UserAccount.objects.filter(id=user_id).first()

    if not user:
        messages.error(request, "User not found")
        return redirect('register')

    otp = generate_otp()
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.save()

    try:
        send_mail(
            'Resend OTP',
            f'Your new OTP is: {otp}',
            settings.EMAIL_HOST_USER,
            [user.email],
        )
        messages.success(request, "New OTP sent")
    except Exception as e:
        print("RESEND ERROR:", e)
        messages.error(request, "Failed to send OTP")

    return redirect('verify_otp')


# ===========================
# LOGIN
# ===========================
def userlogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = UserAccount.objects.filter(email=username).first()

        if not user:
            messages.error(request, "User not found")
            return redirect('userlogin')

        if not user.check_password(password):
            messages.error(request, "Incorrect password")

        elif user.status != 'activated':
            messages.error(request, "Verify email first")

        else:
            request.session['user_id'] = user.id
            return redirect('userhome')

    return render(request, 'userlogin.html')


# ===========================
# USER HOME
# ===========================
def userhome(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('userlogin')

    user = UserAccount.objects.filter(id=user_id).first()
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

            save_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")
            os.makedirs(save_dir, exist_ok=True)

            save_path = os.path.join(save_dir, img_file.name)

            with open(save_path, "wb+") as f:
                for chunk in img_file.chunks():
                    f.write(chunk)

            uploaded_image = f"{settings.MEDIA_URL}uploaded/{img_file.name}"

            # ✅ validation
            try:
                is_cheque, reason = validate_cheque_image(save_path)
            except:
                is_cheque = True

            if not is_cheque:
                return render(request, 'prediction.html', {
                    'form': form,
                    'error': "Invalid Document",
                    'uploaded_image': uploaded_image
                })

            # ✅ PROCESS
            try:
                output = process_cheque(save_path)
            except Exception as e:
                print("PROCESS ERROR:", e)
                output = None

            try:
                details = extract_cheque_details(save_path)
            except Exception as e:
                print("EXTRACT ERROR:", e)
                details = None

            print("DETAILS:", details)
            print("FILE PATH:", save_path)

            request.session['uploaded_image'] = uploaded_image
            request.session['output'] = output
            request.session['details'] = details

            # ✅ OWNER OTP LOGIC (FIXED)
            acc = None
            sent = False

            if details and isinstance(details, dict):
                acc = details.get("Account Number") or details.get("account_number")

                print("ACCOUNT:", acc)

            if acc:
                sent = send_owner_alert(request, acc)

            if sent:
                 return redirect('verify_owner_otp')

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


# ===========================
# CHEQUE SAMPLES
# ===========================
def cheque_samples(request):
    from django.conf import settings

    images = [
        settings.STATIC_URL + "images/sample1.jpg",
        settings.STATIC_URL + "images/sample2.jpg",
    ]

    return render(request, "ChequeSamples.html", {
        "images": images
    })


# ===========================
# MODEL EVALUATION
# ===========================
def model_evaluation(request):
    return render(request, "ModelEvaluation.html")