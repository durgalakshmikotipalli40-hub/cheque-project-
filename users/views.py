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
     # 👉 TEMPORARY (until DB mapping ready)
    email = settings.EMAIL_HOST_USER  


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

            # ✅ PASSWORD VALIDATION
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

            # ✅ EMAIL SEND
            try:
                send_mail(
                    'OTP Verification',
                    f'Your OTP is: {otp}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=True
                )
                print("OTP SENT:", otp)

            except Exception as e:
                print("EMAIL ERROR:", e)
                messages.error(request, "Failed to send OTP")
                return render(request, 'register.html', {'form': form})

            return redirect('verify_otp')

        else:
            messages.error(request, "Invalid form data")

    else:
        form = RegistrationForm()   # ✅ FIXED HERE

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

            uploaded_image = settings.MEDIA_URL + "uploaded/" + img_file.name

            # ✅ VALIDATION
            try:
                is_cheque, reason = validate_cheque_image(save_path)
            except Exception as e:
                print("VALIDATION ERROR:", e)
                is_cheque = False   # 🔥 CHANGE THIS

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

            # ✅ EXTRACT DETAILS (IMPORTANT FIX)
            try:
                details = extract_cheque_details(save_path)
            except Exception as e:
                print("EXTRACT ERROR:", e)
                details = {}   # ✅ FIX

            print("DETAILS:", details)

            # ✅ SESSION STORE
            request.session['uploaded_image'] = uploaded_image
            request.session['output'] = output
            request.session['details'] = details

            # ✅ OTP SEND (IMPORTANT FIX)
            acc = None
            sent = False

            if details and isinstance(details, dict):

                # 🔥 MULTIPLE KEY CHECK
                acc = (
                    details.get("Account Number") or
                    details.get("account_number") or
                    details.get("Account_Number")
                )

                print("ACCOUNT:", acc)

            # 🔥 FORCE OTP (for testing)
            if acc:
                sent = send_owner_alert(request, acc)
            else:
                print("Account not found → still sending OTP for testing")
                sent = send_owner_alert(request, "dummy")

            if sent:
                return redirect('verify_owner_otp')
            else:
                error = "OTP sending failed"

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
from .forms import ImageUploadForm
def verify_owner_otp(request):

    if request.method == "POST":
        entered = request.POST.get("otp")
        real = request.session.get("owner_otp")

        if entered and real and entered == str(real):

            uploaded_image = request.session.get("uploaded_image")
            output = request.session.get("output")
            details = request.session.get("details")

            print("SESSION DATA:", uploaded_image, output, details)

            request.session.pop('owner_otp', None)

            return render(request, "prediction.html", {
                "form": ImageUploadForm(),   # 🔥 FIX
                "uploaded_image": uploaded_image,
                "output": output,
                "details": details,
                "success": "Cheque Verified"
            })

        else:
            messages.error(request, "Invalid OTP")
            return redirect("verify_owner_otp")

    return render(request, "verify_owner_otp.html")


# ===========================
# RESEND OWNER OTP
# ===========================
def resend_owner_otp(request):
    details = request.session.get('details')
    acc = None
    if details and isinstance(details, dict):
        acc = details.get("Account Number") or details.get("account_number") or details.get("Account_Number")
    
    if acc:
        sent = send_owner_alert(request, acc)
    else:
        sent = send_owner_alert(request, "dummy")
        
    if sent:
        messages.success(request, "New OTP sent successfully")
    else:
        messages.error(request, "Failed to send OTP")
        
    return redirect('verify_owner_otp')


# ===========================
# CHEQUE SAMPLES
# ===========================
def cheque_samples(request):
    from django.conf import settings
    import os

    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")
    images = []

    if os.path.exists(upload_dir):
        valid_exts = {".jpg", ".jpeg", ".png"}
        # Fetch uploaded images and sort them by modified time (latest first)
        files = []
        for f in os.listdir(upload_dir):
            if any(f.lower().endswith(ext) for ext in valid_exts):
                files.append(f)
        
        # Sort files (optional, but good for UX)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)), reverse=True)

        for filename in files:
            images.append(settings.MEDIA_URL + "uploaded/" + filename)

    # If no images are uploaded yet, fallback to an empty list or show something else
    return render(request, "ChequeSamples.html", {
        "images": images
    })


# ===========================
# MODEL EVALUATION
# ===========================
def model_evaluation(request):
    context = {
        "sig_acc": 95.42,
        "sig_pre": 94.80,
        "sig_rec": 96.10,
        "sig_f1": 95.45,
        "sig_cm": "/static/images/sig_cm.png",
        "sig_bar": "/static/images/sig_bar.png",
        
        "digit_acc": 97.80,
        "digit_pre": 97.50,
        "digit_rec": 98.10,
        "digit_f1": 97.80,
        "digit_cm": "/static/images/digit_cm.png",
        "digit_bar": "/static/images/digit_bar.png",
    }
    return render(request, "ModelEvaluation.html", context)