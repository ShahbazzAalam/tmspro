from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # The default path for the Django Administration site
    path('admin/', admin.site.urls),
    
    # CRITICAL: This line tells Django to use your 'management.urls' file 
    # for all requests that don't start with 'admin/'.
    path('', include('management.urls')), 
]