from django.contrib import admin
from django.urls import path
from users import views as uviews
from admins import views as adviews
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', uviews.basefunction, name='basefunction'),
    path('userlogin/', uviews.userlogin, name='userlogin'), 
    path('register/', uviews.register, name='register'),

    # ✅ OTP VERIFY (CORRECT)
    path('verify-otp/', uviews.verify_otp, name='verify_otp'),
    path('logout/', uviews.logout_view, name='logout'),

    path('resend-otp/', uviews.resend_otp, name='resend_otp'),

    path('userhome/', uviews.userhome, name='userhome'),
    path("ChequeSamples/", uviews.cheque_samples, name="ChequeSamples"),
    path("prediction/", uviews.prediction, name="prediction"),

    path('verify-owner-otp/', uviews.verify_owner_otp, name='verify_owner_otp'),

    path("model_evaluation/", uviews.model_evaluation, name="model_evaluation"),


    # ==================== ADMIN VIEWS ====================
    path("admin-login/", adviews.adminlogin, name="adminlogin"),
    path("admin-home/", adviews.adminhome, name="adminhome"),
    path("admin-logout/", adviews.adminlogout, name="adminlogout"),
    path('admin-users/', adviews.admin_users_list, name='admin_users_list'),
    path('activate-user/<int:user_id>/', adviews.activate_user, name='activate_user'),
    path('block-user/<int:user_id>/', adviews.block_user, name='block_user'),
    path('unblock-user/<int:user_id>/', adviews.unblock_user, name='unblock_user'),
    path('delete-user/<int:user_id>/', adviews.delete_user, name='delete_user'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)