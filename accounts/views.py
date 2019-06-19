from django.contrib.auth import views

# Create your views here.

def user_logout(request):
	request.user.save()
	return views.LogoutView.as_view()(request)