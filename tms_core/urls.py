from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    # 1. Django Admin Interface
    path('admin/', admin.site.urls),
    
    # 2. Include the 'management' app URLs at the root path ('')
    # This makes http://127.0.0.1:8000/ go to the trip_list view.
    path('', include('management.urls')), 
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
]