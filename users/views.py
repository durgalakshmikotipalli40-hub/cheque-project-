from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import UserAccount
import os
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
import joblib
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from django.core.mail import send_mail
import random
from django.utils import timezone
from .forms import ImageUploadForm
from PIL import Image
from .utils.final_pipeline import process_cheque
from .utils.gemini_extract import extract_cheque_details
from .utils.gemini_validate import validate_cheque_image   # ✅ ADD THIS
from django.contrib import messages

# ===========================
# CHEQUE OWNER EMAIL MAPPING
# ===========================
OWNER_EMAILS = {
    "63080": "durgalakshmikotipalli40@gmail.com",
    "83939487": "owner2@gmail.com",
    "30002010108841": "owner3@gmail.com",
    "630801551452": "owner4@gmail.com",
    "2854101006936": "owner5@gmail.com",
    "911010049001545": "owner6@gmail.com",
}



# ===========================
# OTP Generator
# ===========================
def generate_otp():
    return str(random.randint(100000, 999999))

# ===========================
# OTP send
# ===========================


def send_owner_alert(request, account_number):

     #✅ SAME EMAIL FOR ALL ACCOUNTS
     
    email = "durgalakshmikotipalli40@gmail.com"

    print("Account Number:", account_number)
    print("Mapped Email:", email)

    if not email:
        print("No email found")
        return False

    otp = str(random.randint(100000, 999999))
    request.session['owner_otp'] = otp

    try:
        send_mail(
            subject="Cheque Verification OTP",
            message=f"Your OTP is: {otp}\n\nIf this is not you, take action immediately.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )

        return True   # ❌ print remove chesam (no terminal OTP)

    except Exception as e:
        print("Email Error:", e)
        return False
# ===========================
# BASE VIEW
# ===========================
def basefunction(request):
    return render(request, 'base.html')


# ===========================
# REGISTER VIEW (FINAL FIXED)
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
                fail_silently=False,
            )

            messages.success(request, "OTP sent to email")
            return redirect('verify_otp')

    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


# ===========================
# FORGOT PASSWORD (TEMP)
# ===========================
def forgot_password(request):
    return render(request, 'forgot_password.html')

#  ===========================
#    verify OTP
# ===========================

from django.utils import timezone
from datetime import timedelta

def verify_otp(request):
    user_id = request.session.get('verify_user')

    if not user_id:
        messages.error(request, "Session expired")
        return redirect('register')

    user = UserAccount.objects.get(id=user_id)

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        # ⏱ check expiry (5 mins)
        if user.otp_created_at and timezone.now() > user.otp_created_at + timedelta(minutes=5):
            messages.error(request, "OTP expired. Please request a new one.")
            return redirect('verify_otp')

        if entered_otp == str(user.otp):
            user.status = 'activated'
            user.otp = None
            user.save()

            request.session.flush()

            messages.success(request, "Account verified!")
            return redirect('userlogin')
        else:
            messages.error(request, "Invalid OTP")

    return render(request, 'verify_otp.html')

# ===========================
# resend_otp
# ===========================

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
# Login View
# ===========================
def userlogin(request):
    print("Login view called.")

    if request.method == 'POST':
        print("POST request received for login.")
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Received username: {username}")

        try:
            user = UserAccount.objects.get(username=username)
            print(f"User found: {user.username}, status: {user.status}")

            if not user.check_password(password):
                messages.error(request, "Incorrect password!")
                print("Password incorrect.")
            
            elif user.status == 'waiting':
                messages.warning(request, "Please verify your email first!")

            elif user.status == 'blocked':
                messages.error(request, "Your account is blocked!")

            else:
                # Login success
                request.session['user_id'] = user.id
                messages.success(request, f"Welcome {user.username}!")
                print(f"User {user.username} logged in successfully. Redirecting to userhome.")
                return redirect('userhome')

        except UserAccount.DoesNotExist:
            messages.error(request, "User does not exist!")
            print("User does not exist in DB.")

    else:
        print("GET request received. Rendering login form.")

    return render(request, 'userlogin.html')

# ===========================
# User Home View
# ===========================
def userhome(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "You must login first!")
        print("No session found. Redirecting to login.")
        return redirect('userlogin')

    try:
        user = UserAccount.objects.get(id=user_id)
        print(f"Userhome accessed by: {user.username}")
    except UserAccount.DoesNotExist:
        messages.error(request, "User not found!")
        print("User ID not found in DB. Redirecting to login.")
        return redirect('userlogin')

    return render(request, 'userhome.html', {'user': user})

def logout_view(request):
    user_id = request.session.get('user_id')
    if user_id:
        print(f"Logging out user id: {user_id}")
        request.session.flush()
        messages.success(request, "Logged out successfully!")
    else:
        print("Logout called but no user session found.")
        messages.warning(request, "You are not logged in!")
    return redirect('userlogin')





def cheque_samples(request):
    print("===== DEBUG: Cheque Samples View Loaded =====")

    dataset_dir = os.path.join(
        settings.MEDIA_ROOT,
        "cheque_data/images/train/fixed"
    )

    print("Fixed Dataset Path:", dataset_dir)
    print("Path exists:", os.path.exists(dataset_dir))

    images = []
    if os.path.exists(dataset_dir):
        for f in os.listdir(dataset_dir):
            if f.lower().endswith(".jpg"):
                images.append(f"{settings.MEDIA_URL}cheque_data/images/train/fixed/{f}")

    print("Sending these image URLs:", images[:5])   # print first 5 for debug

    return render(request, "ChequeSamples.html", {
        "images": images
    })




# from django.shortcuts import render
# import os
# from django.conf import settings
# from PIL import Image
# from .forms import ImageUploadForm
# from .utils.final_pipeline import process_cheque
# from .utils.gemini_extract import extract_cheque_details

# def prediction(request):

#     print("\n===== DEBUG: PREDICTION VIEW CALLED =====")

#     uploaded_image = None
#     output = None
#     details = None
#     error = None

#     if request.method == 'POST':
#         print("DEBUG: Received POST request.")

#         form = ImageUploadForm(request.POST, request.FILES)
#         print("DEBUG: Form instantiated.")

#         if form.is_valid():
#             print("DEBUG: Form is VALID.")

#             img_file = form.cleaned_data.get('image')
#             print(f"DEBUG: Cleaned image file = {img_file}")

#             if not img_file:
#                 print("DEBUG: ERROR — img_file is None")
#                 return render(request, 'predictForm1.html', {
#                     'form': form,
#                     'error': "Please upload a cheque image before submitting."
#                 })

#             print(f"DEBUG: MEDIA_ROOT = {settings.MEDIA_ROOT}")
#             print(f"DEBUG: MEDIA_URL = {settings.MEDIA_URL}")

#             save_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")
#             os.makedirs(save_dir, exist_ok=True)
#             print(f"DEBUG: Save directory = {save_dir}")

#             # -------------------------------
#             # 🔥 TIFF → JPG Conversion Here
#             # -------------------------------
#             original_ext = img_file.name.split('.')[-1].lower()

#             img_save_name = img_file.name

#             if original_ext in ["tiff", "tif"]:
#                 print("DEBUG: Detected TIFF image, converting to JPG...")

#                 img = Image.open(img_file)
#                 img = img.convert("RGB")

#                 # Replace .tiff/.tif with .jpg
#                 img_save_name = img_file.name.rsplit('.', 1)[0] + ".jpg"
#                 save_path = os.path.join(save_dir, img_save_name)

#                 img.save(save_path, "JPEG", quality=95)

#                 print(f"DEBUG: Converted TIFF → JPG: {img_save_name}")

#             else:
#                 print("DEBUG: Normal JPG/PNG file uploading...")
#                 save_path = os.path.join(save_dir, img_save_name)
#                 with open(save_path, "wb+") as dest:
#                     for chunk in img_file.chunks():
#                         dest.write(chunk)

#             print(f"DEBUG: Saved File Path = {save_path}")

#             # Build image URL for HTML
#             uploaded_image = f"{settings.MEDIA_URL}uploaded/{img_save_name}"
#             print(f"DEBUG: Uploaded image URL = {uploaded_image}")
#             print("DEBUG: File exists physically:", os.path.exists(save_path))

#             # Process cheque
#             print("DEBUG: Running process_cheque()...")
#             output = process_cheque(save_path)
#             print(f"DEBUG: Result = {output}")

#             # Field extraction
#             print("DEBUG: Running extract_cheque_details()...")
#             details = extract_cheque_details(save_path)
#             print("DEBUG: Extraction complete:", details)

#         else:
#             print("DEBUG: Form INVALID.")
#             print(form.errors)

#     else:
#         print("DEBUG: GET request — empty form loaded.")
#         form = ImageUploadForm()

#     print("===== DEBUG: RETURNING RENDER =====\n")

#     return render(request, 'predictForm1.html', {
#         'form': form,
#         'uploaded_image': uploaded_image,
#         'output': output,
#         'details': details,
#         'error': error
#     })


from django.contrib import messages

from django.contrib import messages

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
                    'error': "Please upload an image"
                })

            save_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")
            os.makedirs(save_dir, exist_ok=True)

            original_ext = img_file.name.split('.')[-1].lower()
            img_save_name = img_file.name

            # ---------------- TIFF → JPG ----------------
            if original_ext in ["tif", "tiff"]:
                img = Image.open(img_file).convert("RGB")
                img_save_name = img_file.name.rsplit('.', 1)[0] + ".jpg"
                save_path = os.path.join(save_dir, img_save_name)
                img.save(save_path, "JPEG", quality=95)
            else:
                save_path = os.path.join(save_dir, img_save_name)
                with open(save_path, "wb+") as f:
                    for chunk in img_file.chunks():
                        f.write(chunk)

            uploaded_image = f"{settings.MEDIA_URL}uploaded/{img_save_name}"

            # ===========================
            # 🔐 GEMINI VALIDATION (ONLY ONCE) ✅ (NEED THIS)
            # ===========================
            try:
                if not request.session.get('validated'):
                    is_cheque, reason = validate_cheque_image(save_path)

                    if is_cheque:
                        request.session['validated'] = True
                else:
                    is_cheque = True
                    reason = "Already validated (session)"

            except Exception as e:
                print("Gemini Error:", e)
                is_cheque = True
                reason = "Gemini skipped due to quota"

            # ❌ INVALID STOP
            if not is_cheque:
                return render(request, 'prediction.html', {
                    'form': form,
                    'uploaded_image': uploaded_image,
                    'error': "❌ Invalid Document",
                    'output': "Please upload a valid bank cheque image",
                    'details': {"reason": reason}
                })

            # ===========================
            # ✅ PROCESS CHEQUE
            # ===========================
            output = process_cheque(save_path)
            details = extract_cheque_details(save_path)

            print("Extracted Details:", details)

            # ===========================
            # 🔥 SESSION STORE (VERY IMPORTANT)
            # ===========================
            request.session['uploaded_image'] = uploaded_image
            request.session['output'] = output
            request.session['details'] = details

            # ===========================
            # 🔐 OTP SEND
            # ===========================
            if details:

                account_number = (
                    details.get("Account Number") or
                    details.get("account_number") or
                    details.get("Account No")
                )

                print("Account Number Found:", account_number)

                if account_number:
                    sent = send_owner_alert(request, account_number)

                    if sent:
                        print("OTP sent")

                        request.session['account_number'] = account_number

                        return redirect('verify_owner_otp')
                    else:
                        print("OTP failed")

                else:
                    print("No account number found!")

        else:
            error = "Invalid form submission"

    else:
        form = ImageUploadForm()

    return render(request, 'prediction.html', {
        'form': form,
        'uploaded_image': uploaded_image,
        'output': output,
        'details': details,
        'error': error
    })




import os
import cv2
import numpy as np
import joblib
import torch
import torch.nn as nn
import torch.nn.functional as F
from django.conf import settings
from django.shortcuts import render
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
import matplotlib.pyplot as plt
from torchvision import datasets, transforms


# ============================================================
#  CNN ARCHITECTURE (same as training)
# ============================================================
class ChequeDigitCNN(nn.Module):
    def __init__(self):
        super(ChequeDigitCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, 64 * 7 * 7)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


# ============================================================
#  SIFT EXTRACTION
# ============================================================
def extract_sift_features(image_path, vector_size=128):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    sift = cv2.SIFT_create()
    kp, desc = sift.detectAndCompute(img, None)

    if desc is None:
        return None

    desc = desc.flatten()

    if len(desc) < vector_size:
        desc = np.pad(desc, (0, vector_size - len(desc)))
    else:
        desc = desc[:vector_size]

    return desc


# ============================================================
#  SAVE CONFUSION MATRIX
# ============================================================
def save_confusion_matrix(y_true, y_pred, name):
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap="Blues")
    plt.colorbar()
    plt.title(name)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")

    for i in range(len(cm)):
        for j in range(len(cm[0])):
            plt.text(j, i, cm[i, j], ha='center', va='center')

    eval_dir = os.path.join(settings.MEDIA_ROOT, "evaluation")
    os.makedirs(eval_dir, exist_ok=True)

    file_path = os.path.join(eval_dir, name.replace(" ", "_") + ".png")
    plt.savefig(file_path)
    plt.close()

    return settings.MEDIA_URL + "evaluation/" + name.replace(" ", "_") + ".png"


# ============================================================
#  SAVE BAR CHART
# ============================================================
def save_bar_chart(metrics_dict, name):
    labels = list(metrics_dict.keys())
    values = list(metrics_dict.values())

    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.ylim(0, 1)
    plt.title(name)

    eval_dir = os.path.join(settings.MEDIA_ROOT, "evaluation")
    os.makedirs(eval_dir, exist_ok=True)

    file_path = os.path.join(eval_dir, name.replace(" ", "_") + ".png")
    plt.savefig(file_path)
    plt.close()

    return settings.MEDIA_URL + "evaluation/" + name.replace(" ", "_") + ".png"


# ============================================================
#  FULL MODEL EVALUATION VIEW
# ============================================================
def model_evaluation(request):

    import os
    import numpy as np
    import joblib
    import torch
    from django.conf import settings
    from django.shortcuts import render
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from torchvision import datasets, transforms

    # ----------------------------------------------------------------------
    # 1️⃣ SIGNATURE SVM MODEL
    # ----------------------------------------------------------------------
    svm_path = os.path.join(settings.MEDIA_ROOT, "signature_model", "svm_signature.pkl")
    scaler_path = os.path.join(settings.MEDIA_ROOT, "signature_model", "svm_scaler.pkl")

    # ❗ FILE CHECK (IMPORTANT)
    if not os.path.exists(svm_path):
        return render(request, "ModelEvaluation.html", {
            "sig_error": f"SVM model not found at: {svm_path}"
        })

    if not os.path.exists(scaler_path):
        return render(request, "ModelEvaluation.html", {
            "sig_error": f"Scaler not found at: {scaler_path}"
        })

    svm = joblib.load(svm_path)
    scaler = joblib.load(scaler_path)

    sig_root = os.path.join(settings.MEDIA_ROOT, "signature_dataset", "Dataset_Signature_Final", "dataset1")

    real_dir = os.path.join(sig_root, "real")
    forge_dir = os.path.join(sig_root, "forge")

    X_sig = []
    y_sig = []

    if os.path.exists(real_dir):
        for f in os.listdir(real_dir):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                feat = extract_sift_features(os.path.join(real_dir, f))
                if feat is not None:
                    X_sig.append(feat)
                    y_sig.append(1)

    if os.path.exists(forge_dir):
        for f in os.listdir(forge_dir):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                feat = extract_sift_features(os.path.join(forge_dir, f))
                if feat is not None:
                    X_sig.append(feat)
                    y_sig.append(0)

    X_sig = np.array(X_sig)
    y_sig = np.array(y_sig)

    if len(X_sig) == 0:
        return render(request, "ModelEvaluation.html", {
            "sig_error": "No signature dataset found!"
        })

    X_scaled = scaler.transform(X_sig)
    y_sig_pred = svm.predict(X_scaled)

    sig_acc = accuracy_score(y_sig, y_sig_pred)
    sig_pre = precision_score(y_sig, y_sig_pred)
    sig_rec = recall_score(y_sig, y_sig_pred)
    sig_f1 = f1_score(y_sig, y_sig_pred)

    sig_cm_img = save_confusion_matrix(y_sig, y_sig_pred, "Signature Confusion Matrix")
    sig_bar_img = save_bar_chart(
        {"Accuracy": sig_acc, "Precision": sig_pre, "Recall": sig_rec, "F1": sig_f1},
        "Signature Metrics"
    )

    # ----------------------------------------------------------------------
    # 2️⃣ DIGIT CNN MODEL
    # ----------------------------------------------------------------------
    cnn_path = os.path.join(settings.MEDIA_ROOT, "digit_cnn.pth")

    if not os.path.exists(cnn_path):
        return render(request, "ModelEvaluation.html", {
            "digit_error": f"CNN model not found at: {cnn_path}"
        })

    digit_model = ChequeDigitCNN()
    digit_model.load_state_dict(torch.load(cnn_path, map_location="cpu"))
    digit_model.eval()

    mnist_path = os.path.join(settings.MEDIA_ROOT, "mnist")

    transform = transforms.Compose([
        transforms.Grayscale(),
        transforms.Resize((28, 28)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    test_dataset = datasets.MNIST(mnist_path, train=False, download=True, transform=transform)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=64, shuffle=False)

    y_true = []
    y_pred = []

    with torch.no_grad():
        for images, labels in test_loader:
            outputs = digit_model(images)
            _, predict = torch.max(outputs, 1)
            y_true.extend(labels.numpy())
            y_pred.extend(predict.numpy())

    digit_acc = accuracy_score(y_true, y_pred)
    digit_pre = precision_score(y_true, y_pred, average="macro")
    digit_rec = recall_score(y_true, y_pred, average="macro")
    digit_f1 = f1_score(y_true, y_pred, average="macro")

    digit_cm_img = save_confusion_matrix(y_true, y_pred, "Digit CNN Confusion Matrix")
    digit_bar_img = save_bar_chart(
        {"Accuracy": digit_acc, "Precision": digit_pre, "Recall": digit_rec, "F1": digit_f1},
        "Digit CNN Metrics"
    )

    # ----------------------------------------------------------------------
    # 3️⃣ RETURN
    # ----------------------------------------------------------------------
    return render(request, "ModelEvaluation.html", {
        "sig_acc": sig_acc,
        "sig_pre": sig_pre,
        "sig_rec": sig_rec,
        "sig_f1": sig_f1,
        "sig_cm": sig_cm_img,
        "sig_bar": sig_bar_img,

        "digit_acc": digit_acc,
        "digit_pre": digit_pre,
        "digit_rec": digit_rec,
        "digit_f1": digit_f1,
        "digit_cm": digit_cm_img,
        "digit_bar": digit_bar_img,
    })


# ===========================
# VERIFY OWNER OTP
# ===========================
def verify_owner_otp(request):

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        real_otp = request.session.get("owner_otp")

        if entered_otp == real_otp:

            # ✅ GET DATA
            uploaded_image = request.session.get("uploaded_image")
            output = request.session.get("output")
            details = request.session.get("details")

            validated = request.session.get('validated')

            # 🔥 CLEAR SESSION
            request.session.flush()

            # 🔄 restore validated
            if validated:
                request.session['validated'] = True

            # ✅ SAME PAGE RESULT
            return render(request, "prediction.html", {
                "uploaded_image": uploaded_image,
                "output": output,
                "details": details,
                "success": "✅ Cheque Verified Successfully"
            })

        else:
            return render(request, "verify_owner_otp.html", {
                "error": "❌ Invalid OTP"
            })

    return render(request, "verify_owner_otp.html")