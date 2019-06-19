# Create your views here.

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django import forms
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
from chatgroup.forms import (ChatRoomForm, MessageForm, JoinRoomForm, ChangeRoomForm, FileMessageForm,
    NewChatRoomForm, FindChatroomForm, XJoinRoomForm, UserSignupForm, UserLoginForm, UpdateRoomForm)
from chatgroup.models import Message, ChatGroup
from django.http import JsonResponse
from django.core import serializers
from django.shortcuts import redirect, get_object_or_404, resolve_url, render_to_response, render
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import uuid, json
from chatgroup.utils import uuid_or_redirect, object_to_dict, object2AttrDict, model2Json
from django.middleware.csrf import rotate_token
# from django.contrib.auth.forms import UserCreationForm
from django_registration.backends.one_step.views import RegistrationView
from django.utils import timezone
from django.template import loader
from django.template.context import make_context
from django.template.base import Template
from pprint import pprint

User = get_user_model()

class AjaxableResponseMixin:
    callback_save = None
    ajax_template_name = None

    def form_invalid(self, form):
        print("form_invalid")
        response = super().form_invalid(form)
        if self.request.is_ajax():
            errors = self.get_json_error(form)
            print("form.json_errors:\n", errors)
            return JsonResponse(data=errors, status=400, safe=False)
        else:
            return response

    def form_valid(self, form):
        print("form_valid")
        response = super().form_valid(form)
        # form.save()  # auto run as working with createView
        if callable(self.callback_save):
            self.callback_save(form)
        if self.request.is_ajax():
            # print('cleaned_data:', form.cleaned_data)
            data = self.get_json_data(form)
            # pprint(data)
            return JsonResponse(data=data, safe=False)
        else:
            return response

    def get_json_data(self, form):
        raise NotImplementedError

    def get_json_error(self, form):
        raise NotImplementedError

    def get_ajax(self, request, status=200, **kwargs):
        raise NotImplementedError

# @login_required
# def new_message(request):
#     form = modelform_factory(Message, fields=('msg_type', 'from_user', 'to_group', 'to_user', 'content'))
#     return CreateView.as_view(template_name='chatgroup/new_message.html',
#                               form_class= form, success_url=reverse('chatroom'))(request)

MSG_TYPE_CHOICES = dict(Message.MSG_TYPE_CHOICES)
# @login_required() DO NOT USE IT HERE, MUST BE USED FOR A FUNCITON, TURN TO URLPATTERNS,OR ADD LoginRequiredMixin in View
class ChatRoomCreateView(CreateView):
    template_name = 'chatgroup/new_chatroom.html'
    form_class = ChatRoomForm

    def get_initial(self):
        if self.request.method=='GET':
            if isinstance(self.request.user, User):
                return {
                    'manager': self.request.user,
                    'members': self.request.user,
                }
        return {}

class NewChatRoomCreateView(AjaxableResponseMixin, CreateView):
    template_name = 'chatgroup/new_chatroom.html'
    form_class = NewChatRoomForm

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            form =  self.form_class()
            # form =  self.form_class(initial=self.get_initial())
            data = self.get_json_error(form)
            return JsonResponse(data=data, safe=False)
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return "/chatcenter/"

    def get_json_data(self, form):
        group = object_to_dict(form.instance)
        group.update({"members":self.object.members.count()})
        data = {
            "messages":"created NewChatRoomForm",
            "redirect":self.request.GET.get('next', False) or self.get_success_url(),
            "chatgroup":group,
        }
        return data

    def get_json_error(self, form):
        res = render(self.request, "chatgroup/newroomform.html", {"form":form})
        return {
            "form":res.content.decode(),
        }

    def form_valid(self, form):
        # foreignkey required column must be set before form.save()
        form.instance.manager = self.request.user
        form.instance.check_opening_status()
        # many2many cannot be set before form.save(), else raise
        # django.db.utils.IntegrityError: FOREIGN KEY constraint failed
        # to fix it, it need set it after form.instance.save,
        # exp:define a callback_after_save() and will be called in right time,then save it
        # form.instance.members.add(self.request.user)
        def callback_after_save(form):
            # for this model, manager is required, so it should be set before form.save()
            # form.instance.manager = self.request.user
            form.instance.members.set([self.request.user,])
            form.instance.save()
        # print(form.instance.__dict__)
        self.callback_save = callback_after_save
        return super().form_valid(form)


class ChatRoomView(AjaxableResponseMixin, CreateView):
    template_name = 'chatgroup/chatroom.html'
    form_class = MessageForm
    # use fields just with specify model, but not with form_class
    # fields = ['msg_type', 'from_user', 'to_group', 'to_user', 'content']
    # success_url will be called by self.get_success_url(), just for httpresponse not for jsonresponse
    success_url = '/channel/{pk}/'

    @uuid_or_redirect(to_url='newchatroom')
    def get(self, request, *args, **kwargs):
        if self.request.user in self.chatgroup.members.all():
            return super().get(request, *args, **kwargs) 
        else:
            return redirect('joinroom', pk=self.chatroom_id)
    
    @uuid_or_redirect(to_url='newchatroom')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        if self.request.method == 'GET':
            initial = {
                'to_group': self.chatroom_id,
                'from_user': self.request.user.pk,
            }
        else:
            initial = {}
        return initial

    def get_success_url(self):
        return self.success_url.format(pk=self.chatroom_id)

    def get_json_data(self, form):
        return form.cleaned_data

class ChangeRoomView(AjaxableResponseMixin, UpdateView):
    template_name = 'chatgroup/join_chatroom.html'
    form_class = ChangeRoomForm
    # model = ChatGroup
    success_url = '/channel/{pk}/'

    @uuid_or_redirect(to_url='newchatroom')
    def dispatch(self, request, *args, **kwargs):
        if request.user is self.chatgroup.manager:
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('joinroom', pk=self.chatroom_id)

    def get_success_url(self):
        return self.success_url.format(pk=self.chatroom_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'join_user':self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_object(self):
        return get_object_or_404(ChatGroup, group_uuid=self.chatroom_id)


class XJoinRoomView(AjaxableResponseMixin, FormView):
    template_name = 'chatgroup/join_chatroom.html'
    form_class = XJoinRoomForm
    success_url = '/chatcenter/'

    def get(self, request, *args, **kwargs):
        # print("?g=", self.request.GET.get('g', None))
        if request.is_ajax():
            form = self.form_class(self.request.user, initial = self.get_initial())
            data = self.get_json_error(form)
            return JsonResponse(data=data, safe=False)
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"join_user":self.request.user})
        return kwargs

    def get_success_url(self):
        return "/chatcenter/"

    def get_json_data(self, form):
        if not self.request.user.is_anonymous:
            self.request.user.save()
        group = object_to_dict(self.object)
        group.update({"members":self.object.members.count()})
        
        data = {
            "messages":"Joined a ChatRoom named "+self.object.group_name,
            "redirect":self.request.GET.get('next', None) or self.get_success_url(),
            "chatgroup":group,
            "already_joined":self.already_joined,
        }
        return data

    def get_json_error(self, form):
        res = render(self.request, 
            "chatgroup/joinroomform.html", {
            "form":form,
            "next":self.request.GET.get('next', None),
            })
        return {
            "form":res.content.decode(),
        }

    def get_initial(self):
        return {
        'group_uuid':self.request.GET.get('g', None),
        }

    def form_valid(self, form):
        if self.request.user in form.chatgroup.members.all():
            self.already_joined = True
        else:
            self.already_joined = False
        self.object = form.save()
        return super().form_valid(form)

class JoinRoomView(AjaxableResponseMixin, FormView):
    template_name = 'chatgroup/join_chatroom.html'
    form_class = JoinRoomForm
    success_url = '/channel/{pk}/'

    @uuid_or_redirect(to_url='newchatroom')
    def get(self, request, *args, **kwargs):
        if request.user in self.chatgroup.members.all():
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    @uuid_or_redirect(to_url='newchatroom')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.success_url.format(pk=self.chatroom_id)

    def get_initial(self):
        if self.request.method == 'GET':
            return {
                'group_uuid': self.chatgroup.pk,
            }
        else:
            return {}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'join_user':self.request.user,
            'chatgroup':self.chatgroup,
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class XChatRoomView(AjaxableResponseMixin, CreateView):
    
    template_name = 'chatgroup/chatcenter.html'
    form_class = FileMessageForm
    # use fields just with specify model, but not with form_class
    # fields = ['msg_type', 'from_user', 'to_group', 'to_user', 'content']
    # success_url will be called by self.get_success_url(), just for httpresponse not for jsonresponse
    success_url = '/chatcenter/'

    # @uuid_or_redirect(to_url='newchatroom')
    # def get(self, request, *args, **kwargs):
    #     if self.request.user in self.chatgroup.members.all():
    #         return super().get(request, *args, **kwargs) 
    #     else:
    #         return redirect('joinroom', pk=self.chatroom_id)
    
    # @uuid_or_redirect(to_url='newchatroom')
    # def post(self, request, *args, **kwargs):
    #     return super().post(request, *args, **kwargs)

    def get_initial(self):
        if self.request.method == 'GET':
            initial = {
                # 'to_group': self.chatroom_id,
                'from_user': self.request.user.pk,
                'msg_type': 2,
            }
        else:
            initial = {}
        return initial

    def get_success_url(self):
        return self.success_url

    def get_json_data(self, form):
        # print("model2Json:", model2Json(form.instance))
        # print("object2AttrDict:", object2AttrDict(form.instance))
        i = form.instance.msg_type
        print(self.object)
        if i == 1:
            return {'message':'text message saved.'}
        extra_data = {
            'msg_type':MSG_TYPE_CHOICES[i].lower(),
            'from_username':form.instance.from_user.username,
            'mid':self.request.POST.get('mid'),
            'msgFileName':self.request.POST.get("msgFileName"),
            # 'to_group':form.instance.to_group.pk,
        }
        data = object_to_dict(self.object)
        # print(data)      
        # print(dir(data['image']),'\n', dir(form), '\n', dir(data['file']))
        data.update(extra_data)
        # print('json_data:\n',data)
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chatgroups = self.request.user.user_joined_groups.all()
        context.update({
            "chatgroups": chatgroups,
            })
        # print('context:\n',context)
        return context

class AjaxableLoginView(AjaxableResponseMixin, LoginView):
    template_name = "accounts/login.html"
    success_url = "/"
    form_class = UserLoginForm

    def dispatch(self, request, *args, **kwargs):
        # print("dispatch login")
        tz_offset = self.request.POST.get('tz_offset', None)
        # print(tz_offset)
        if isinstance(tz_offset, str):
            tz_offset = int(tz_offset)
        if tz_offset:
            self.request.session['tz_offset'] = -tz_offset
            # print(self.request.session.items())
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # print('login next:\n', self.request.GET.get('next', False))
        if request.user.is_authenticated:
            return redirect(self.request.GET.get('next', False) or self.get_success_url())
        if request.is_ajax():
            form = self.form_class()
            data = self.get_json_error(form)
            return JsonResponse(data=data, safe=False)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # print(request.META)
        # if render method pass the request param, it dont need set the following code
        # request.META["CSRF_COOKIE"] = rotate_token(request)
        return super().post(request, *args, **kwargs)

    def get_json_error(self, form):
        # it works that the render method pass the request param to update csrf_token, 
        # but render_to_response cannot update csrf_token, else
        # if want to fix it, need pass context_instance=RequestContext(request)
        res = render(self.request, "accounts/loginform.html", {"form":form})
        data = {
            "form":res.content.decode(),
        }
        return data

    def get_json_data(self, form):
        tz_offset = self.request.POST.get('tz_offset', None)
        if isinstance(tz_offset, str):
            tz_offset = int(tz_offset)
        if tz_offset:
            self.request.session['tz_offset'] = -tz_offset
            self.request.session.save()
        print(self.request.session.items())
        data = {
            "message":"Welcome, "+self.request.user.get_username(),
            "redirect": self.request.GET.get('next', False) or self.get_success_url(),
        }
        # print(data)
        return data

    def get_success_url(self):
        # print(self.request.user.user_joined_groups.all())
        if self.request.user.user_joined_groups.all():
            return "/chatcenter/"
        return "/"

class UserSignupView(AjaxableResponseMixin, RegistrationView):
    template_name = "accounts/signup.html"
    success_url = "/"
    form_class = UserSignupForm

    def dispatch(self, request, *args, **kwargs):
        # print("dispatch signup")
        tz_offset = self.request.POST.get('tz_offset', None)
        # print(tz_offset)
        if isinstance(tz_offset, str):
            tz_offset = int(tz_offset)
        if tz_offset:
            self.request.session['tz_offset'] = -tz_offset
            # print(self.request.session.items())
        return super().dispatch(request, *args, **kwargs)

    def get_json_error(self, form):
        res = render(self.request, "accounts/signupform.html", {"form":form})
        return {
            "form":res.content.decode(),
        }

    def get_json_data(self, form):

        data = {
            "message":"Welcome, "+self.request.user.get_username(),
            "redirect": self.request.GET.get('next', False) or "/",
        }
        return data

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            form = self.form_class()
            data = self.get_json_error(form)
            return JsonResponse(data=data, safe=False)
        return super().get(request, *args, **kwargs)

class UserDeletemeView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        is_safe_delete = self.request.GET.get("command", None)
        if is_safe_delete:
            self.delete_user_safe()
        request.user.delete()
        messages.success(request, _("Your account has been deleted."))
        # print(request._messages.__dict__)
        return super().dispatch(request, *args, **kwargs)

    def delete_user_safe(self):
        as_manager_groups = self.request.user.chatgroups.all()
        for group in as_manager_groups:
            group.change_manager(self)

class ChatGroupDetailView(AjaxableResponseMixin, DetailView):
    template_name = 'chatgroup/chatgroup_detail.html'
    ajax_template_name = 'chatgroup/chatgroup_detail_table.html'
    model = ChatGroup
    success_url = "/detailroom/{pk}/"

    @uuid_or_redirect(to_url='newchatroom')
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.is_ajax():
            res = render(request, self.ajax_template_name, self.get_context_data(**kwargs))
            return JsonResponse(data={"content":res.content.decode()}, safe=False)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        use_tz = timezone.get_fixed_timezone(self.request.session.get('tz_offset', 0))
        context['use_tz'] = use_tz or timezone.get_current_timezone()
        print(context)
        print(self.request.session.items())
        return context

    def get_object(self):
        if self.request.is_ajax():
            return self.chatgroup
        else:
            return super().get_object()

    def get_ajax(self, request, status=200, **kwargs):
        res = render(request, self.ajax_template_name, kwargs)
        return JsonResponse(data={'messages': res.content.decode()}, status=status, safe=False)

class XUpdateRoomView(AjaxableResponseMixin, UpdateView):
    template_name = 'chatgroup/chatgroup_update.html'
    ajax_template_name = 'chatgroup/chatgroup_update_form.html'
    ajax_error_template_name = 'chatgroup/chatgroup_update_error.html'
    form_class = UpdateRoomForm
    model = ChatGroup
    success_url = '/update/{pk}/'

    @uuid_or_redirect(to_url='newchatroom')
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        command = self.request.GET.get('command', None)
        if request.user == self.chatgroup.manager:
            if command and command == "delete":
                try:
                    self.object.delete()
                    return JsonResponse(data={'messages':"The chatgroup has been deleted.", 'gid':self.chatroom_id, 'group_name':self.object.group_name}, safe=False)
                except:
                    return JsonResponse(data={'messages':"Errors raised when deleting the chatgroup."}, status=400, safe=False)
            return super().dispatch(request, *args, **kwargs)
        elif command and command == 'leave':
            self.chatgroup.members.remove(request.user)
            return JsonResponse(data={'messages':"You have left the chatroom.", 'gid':self.chatroom_id, 'group_name':self.chatgroup.group_name}, safe=False)
        elif request.user not in self.chatgroup.members.all():
            return self.get_ajax(request, status=200, **{'pk':self.chatroom_id, 'iderror':'Rejected by server, You are not a member of this chatgroup', 'command':'remove'})
        else:
            return redirect('detailroom', pk=self.chatroom_id)

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request, status=200, **(self.get_context_data() or {}))
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return self.success_url.format(pk=self.chatroom_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        use_tz = timezone.get_fixed_timezone(self.request.session.get('tz_offset', 0))
        context['use_tz'] = use_tz or timezone.get_current_timezone()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'join_user':self.request.user,
        })
        return kwargs

    def get_object(self):
        if self.request.is_ajax():
            return self.chatgroup
        else:
            return super().get_object()

    def get_ajax(self, request, status=200, **kwargs):
        err = kwargs.get("iderror", None)
        print("err:", err)
        if err:
            res = render(request, self.ajax_error_template_name, kwargs)
        else:
            res = render(request, self.ajax_template_name, kwargs)
            # print(self.request.session.items())
            # use_tz = timezone.get_fixed_timezone(self.request.session.get('tz_offset', 0))
            # context = make_context(self.get_context_data(**kwargs), request=self.request, use_tz=use_tz)
            # print(context.__dict__)
            # template = loader.get_template(self.ajax_template_name).template
            # content = template.render(context)
            # print(content)
        # return JsonResponse(data={'content': str(content)}, status=status, safe=False)
        return JsonResponse(data={'content': res.content.decode()}, status=status, safe=False)

    def get_json_error(self, form):
        res = render(self.request, self.ajax_template_name , {"form":form})
        data = {
            "content":res.content.decode(),
        }
        return data

    def get_json_data(self, form):
        data = {
            "messages":"ChatGroup information update completed.",
            "redirect": self.request.GET.get('next', False) or self.get_success_url(),
            "chatgroup": object_to_dict(form.instance),
            "remove_users": self.remove_users if self.need_remove_users else None,
        }
        return data

    def form_valid(self, form):
        self.need_remove_users = False
        if form.cleaned_data['members'].count() < form.instance.members.count():
            self.need_remove_users = True
            self.remove_users = form.instance.members.difference(form.cleaned_data['members'])
            self.remove_users = list(self.remove_users.values('pk', 'username'))
            print('remove_users', self.remove_users)
        return super().form_valid(form)