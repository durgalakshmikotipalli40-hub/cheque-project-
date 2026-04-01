import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================
# 🔐 SECURITY
# ============================

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True

ALLOWED_HOSTS = ["*"]


# ============================
# APPS
# ============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'admins',
]

# ============================
# MIDDLEWARE
# ============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

     # ADD THIS 👇
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chequeprojet.urls'

# ============================
# TEMPLATES
# ============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'chequeprojet.wsgi.application'

# ============================
# DATABASE
# ============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================
# PASSWORD VALIDATION
# ============================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================
# LANGUAGE & TIME
# ============================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True
USE_TZ = True

# ============================
# STATIC FILES
# ============================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # optional

# ADD THIS 👇
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================
# MEDIA FILES
# ============================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================
# 📧 EMAIL CONFIG
# ============================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")