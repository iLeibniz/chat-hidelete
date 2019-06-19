# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.contrib.auth import views
from django.urls import path, reverse
from chatgroup.views import AjaxableLoginView
from accounts.views import user_logout
urlpatterns = [
    path('login/', AjaxableLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
]
