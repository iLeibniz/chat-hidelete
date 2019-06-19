# -*-coding:utf8-*-
"""hidel URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
# from django.contrib.auth.forms import UserCreationForm
from django.views.generic.base import TemplateView
from django.urls import path, include
from chatgroup.views import (XChatRoomView, UserSignupView, NewChatRoomCreateView, XJoinRoomView, 
    UserDeletemeView, ChatGroupDetailView, XUpdateRoomView)

urlpatterns = [
    path('', TemplateView.as_view(template_name="registration/index.html"), {'display_meta': False},
         name='index'),
    path('chatcenter/', login_required(XChatRoomView.as_view()), name='chatcenter'),
    path('deleteme/', login_required(UserDeletemeView.as_view()), name='deleteme'),
    path('accounts/signup/', UserSignupView.as_view(), name='signup'),
    path('pushdown4admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('newchatroom/', login_required(NewChatRoomCreateView.as_view()), name='newchatroom'),
    path('update/<pk>/', login_required(XUpdateRoomView.as_view())),
    path('update/', login_required(XUpdateRoomView.as_view()), name='updateroom'),
    path('detail/<pk>/', login_required(ChatGroupDetailView.as_view()), name='detailroom'),
    path('xjoin/', login_required(XJoinRoomView.as_view()), name='xjoinroom'),
]
