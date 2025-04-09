from django.urls import path
from . import views  # Import your custom views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('store/dashboard/', views.store_dashboard, name='store_dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('admin/edit_user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin/delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('store/process_payment/', views.process_payment, name='process_payment'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('top-up-history/', views.top_up_history, name='top_up_history'),
    path('purchase-history/', views.purchase_history, name='purchase_history'),
    path('approve_user/<int:user_id>/', views.approve_user, name='approve_user'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
