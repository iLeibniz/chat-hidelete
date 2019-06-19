from django.forms import ModelForm, Form, HiddenInput, Textarea, ImageField
from django import forms
from chatgroup.models import ChatGroup, Message, CHECKIN_TAGS
from django.forms.forms import BaseForm, DeclarativeFieldsMetaclass
from django_registration.forms import RegistrationForm
# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext, gettext_lazy as _
from chatgroup.models import CHECKIN_TAGS
import uuid, random
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from chatgroup.utils import AVATAR_LIST, AVATAR_LEN

User = get_user_model()

delta = timedelta(days = settings.GROUP_LIFE_DATES)
join_delta = timedelta(minutes=settings.DEFAULT_JOIN_DELTA_TIME)

def get_default_avatar_image():
    return AVATAR_LIST[random.randint(0, AVATAR_LEN)]

class ChatRoomForm(ModelForm):
    class Meta:
        model = ChatGroup
        fields = ('group_name', 'group_info', 'manager', 'members', 'checkin_method',
                  'invite_code', 'join_question', 'join_answer', 'join_deltatime')
        widgets = {
            # 'manager':forms.HiddenInput(),
            # 'members':forms.HiddenInput(),
        }

class NewChatRoomForm(ModelForm):
    error_messages = {
        'invalid_code': _(
            "Please enter a valid %(invite_code)s."
        ),
        'invalid_answer': _("your answer is empty, Please enter a answer."),
        'invalid_manager':_("you has no permission to update the chatgroup info."),
    }

    class Meta:
        model = ChatGroup
        fields = ('group_name', 'group_info', 'invite_code', 'join_deltatime')
        widgets = {
            'group_name':forms.TextInput(attrs={'class':'form-control'}),
            'group_info':forms.Textarea(attrs={'class':'form-control', 'rows':2}),
            'invite_code':forms.TextInput(attrs={'class':'form-control'}),
            'join_deltatime':forms.TextInput(attrs={'class':'form-control'}),
            # 'manager':forms.Select(attrs={'class':'form-control', }),
            # 'members':forms.SelectMultiple(attrs={'class':'form-control', }),
        }

    def clean_invite_code(self):
        invite_code = self.cleaned_data.get('invite_code')
        # if self.cleaned_data.get('checkin_method') == CHECKIN_TAGS.IC:
        if len(invite_code) < 8:
            raise self.get_invalid_error('invalid_code', 'invite_code')
        return invite_code

    def get_invalid_error(self, error_name, error_field_name):
        error_field = ChatGroup._meta.get_field(error_field_name)
        print('verbose_name:', error_field.verbose_name)
        return forms.ValidationError(
            self.error_messages[error_name],
            code=error_name,
            params={error_field_name: error_field.verbose_name},
        )

    def save(self):
        self.instance.group_image = get_default_avatar_image()
        return super().save()

class ChangeRoomForm(ModelForm):
    error_messages = {
        'invalid_code': _(
            "Please enter a correct %(invite_code)s. Note that field may be case-sensitive."
        ),
        'invalid_answer': _("your answer is empty, Please enter a answer."),
    }

    def __init__(self, join_user, *args, **kwargs):
        self.join_user = join_user
        super().__init__(*args, **kwargs)

    class Meta:
        model = ChatGroup
        fields = ('group_uuid', 'group_name', 'group_info', 'manager', 'members', 'checkin_method',
                  'invite_code', "join_question", 'join_answer', 'join_deltatime')
        widgets = {
            'group_uuid':forms.HiddenInput(),
        }

    def clean_invite_code(self):
        invite_code = self.cleaned_data.get('invite_code')
        if self.cleaned_data.get('checkin_method') == CHECKIN_TAGS.IC:
            if len(invite_code) < 6:
                raise self.get_invalid_join_error('invalid_code', 'invite_code')
        return invite_code

    def clean_join_answer(self):
        answer = self.cleaned_data.get('join_answer')
        if self.cleaned_data.get('checkin_method') == CHECKIN_TAGS.QA:
            if len(answer) < 1:
                raise self.get_invalid_join_error('invalid_answer', 'join_answer')
        return answer

    def clean(self):
        # invite_code = self.cleaned_data.get('invite_code')
        # join_answer = self.cleaned_data.get('join_answer')
        print('ChangeRoomForm, clean:', self.cleaned_data)
        return self.cleaned_data

    def get_invalid_join_error(self, error_name, error_field_name):
        error_field = ChatGroup._meta.get_field(error_field_name)
        print('verbose_name:', error_field.verbose_name)
        return forms.ValidationError(
            self.error_messages[error_name],
            code=error_name,
            params={error_field_name: error_field.verbose_name},
        )
 

class JoinRoomForm(Form):
    """method 1nd :mix customize widget
    """
    group_uuid = forms.HiddenInput()
    invite_code = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'autofocus':True}), help_text="Please type invite-code")
    join_answer = forms.CharField(max_length=150, required=False, help_text='Please type answer')
 
    error_messages = {
        'invalid_code': _(
            "Please enter a correct invite_code. Note that field may be case-sensitive."
        ),
        'invalid_answer': _("your answer is incorrect, Please enter the correct one."),
        'invalid_groupid':_("groupid is invalid, maybe it has been deleted. try again or another group!"),
    }

    def __init__(self, join_user, chatgroup, *args, **kwargs):
        self.user = join_user
        self.chatgroup = chatgroup
        super().__init__(*args, **kwargs)

    def clean(self):
        print("Form clean:", self.cleaned_data) 
        return self.cleaned_data

    def clean_invite_code(self):
        print('clean_invite_code:', self.cleaned_data)
        code = self.cleaned_data.get('invite_code')
        if self.chatgroup and self.chatgroup.checkin_method == CHECKIN_TAGS.IC:
            if self.chatgroup.check_passport(invite_code=code):
                return code
        raise forms.ValidationError(
            self.error_messages['invalid_code'],
            code='invalid_code',
        )
        

    def clean_join_answer(self):
        print('clean_join_answer:', self.cleaned_data)
        answer = self.cleaned_data.get('join_answer')
        if self.chatgroup and self.chatgroup.checkin_method == CHECKIN_TAGS.QA: 
            if self.chatgroup.check_passport(join_answer=answer):
                return answer
        raise forms.ValidationError(
            self.error_messages['invalid_answer'],
            code='invalid_answer',
        )

    def save(self):
        if self.user and isinstance(self.user, User):
            self.chatgroup.members.add(self.user)
            self.chatgroup.save()
        return self.chatgroup

class XJoinRoomForm(Form):
    group_uuid = forms.CharField(label=_('group uuid'), max_length=300, min_length=32,
        widget=forms.TextInput(attrs={'autofocus':True, 'class':'form-control'}),
        help_text="Please type chatroom address that is a long random string.")
    invite_code = forms.CharField(label=_('invite code'), max_length=30, help_text="Please type invite-code",
        widget=forms.TextInput(attrs={'class':'form-control'}))
 
    error_messages = {
        'invalid_code': _(
            "Please enter a correct invite_code. Note that field may be case-sensitive."
        ),
        'invalid_groupid':_("chatroom address is wrong or invalid!"),
        'chatroom_closed':_("chatroom has been closed, ask the manager for reopen it."),
        'members_limit':_("chatroom members's count is limited, you can't join."),
    }

    def __init__(self, join_user, *args, **kwargs):
        self.gid = None
        self.user = join_user
        self.chatgroup = None
        super().__init__(*args, **kwargs)

    def clean_invite_code(self):
        print('clean_invite_code:', self.cleaned_data)
        code = self.cleaned_data.get('invite_code')
        if self.chatgroup and self.chatgroup.checkin_method == CHECKIN_TAGS.IC:
            if self.chatgroup.check_passport(invite_code=code):
                return code
            else:
                raise forms.ValidationError(
                        self.error_messages['invalid_code'],
                        code='invalid_code',
                    )

    def clean_group_uuid(self):
        print('clean group_uuid:', self.cleaned_data)
        group_uuid = self.cleaned_data.get('group_uuid')
        is_valid_uuid = False
        if isinstance(group_uuid, str):
            gids = group_uuid.split('/')
            print('gids:', gids)
            for value in gids:
                try:
                    if len(value)>=35 and value.startswith('?g='):
                        value = value.split("=")[1]
                        print(value)
                    self.gid = uuid.UUID(value)
                    is_valid_uuid = True
                    break
                except ValueError as e:
                    is_valid_uuid = False
            try:
                self.chatgroup = ChatGroup.objects.get(pk=self.gid)
            except ChatGroup.DoesNotExist as e:
                is_valid_uuid = False
                self.chatgroup = False
        if not is_valid_uuid:
            raise forms.ValidationError(
                self.error_messages['invalid_groupid'],
                code='invalid_groupid',
            )
        return self.gid or group_uuid

    def clean(self):
        is_opening = None
        if self.chatgroup:
            if self.chatgroup.members.count() >= settings.CHAT_MEMBERS_LIMIT:
                raise forms.ValidationError(
                    self.error_messages['members_limit'],
                    code='members_limit',
                )
            is_opening = self.chatgroup.check_opening_status()
        if self.chatgroup and is_opening == False:
            raise forms.ValidationError(
                self.error_messages['chatroom_closed'],
                code='chatroom_closed',
            )
        return self.cleaned_data

    def save(self):
        if self.user and isinstance(self.user, User):
            self.chatgroup.members.add(self.user)
            self.chatgroup.save()
        return self.chatgroup

class FindChatroomForm(Form):
    group_uuid = forms.CharField(max_length=300, min_length=32,
        widget=forms.TextInput(attrs={'autofocus':True, 'class':'form-control'}),
        help_text="Please type chatroom address that is a long random string.")
    error_messages = {
        'invalid_groupid':_("chatroom address is wrong or invalid!"),
    }

    def clean_group_uuid(self):
        print('clean group_uuid:', self.cleaned_data)
        group_uuid = self.cleaned_data.get('group_uuid')
        is_valid_uuid = False
        if isinstance(gid, str):
            gids = gid.split('/')
            for value in gids:
                try:
                    self.gid = uuid.UUID(value)
                    is_valid_uuid = True
                    break
                except ValueError as e:
                    is_valid_uuid = False
            try:
                self.chatgroup = ChatGroup.object.get(pk=self.gid)
            except DoesNotExist as e:
                is_valid_uuid = False
        if not is_valid_uuid:
            raise forms.ValidationError(
                self.error_messages['invalid_groupid'],
                code='invalid_groupid',
            )
        return self.gid

class MessageForm(ModelForm):
    """method 2nd :mix customize widget for modelForm
    """
    class Meta:
        model = Message
        fields = ('msg_type', 'from_user', 'to_group', 'to_user', 'content', 'image')
        widgets = {
            'msg_type': HiddenInput(attrs={'value': 1}),
            'from_user': HiddenInput(),
            'to_group': HiddenInput(),
            'to_user': HiddenInput(attrs={'required': False}),
            'content': Textarea(attrs={'rows': 2, }),
            # 'image':ImageField(),
        }

class FileMessageForm(ModelForm):
    """method 2nd :mix customize widget for modelForm
    """
    class Meta:
        model = Message
        fields = ('msg_type', 'from_user', 'to_group', 'to_user', 'content', 'image', 'video', 'file')
        widgets = {
            'msg_type': HiddenInput(),
            'from_user': HiddenInput(),
            'to_group': HiddenInput(attrs={'value': ""}),#cee77dba-879c-4334-a9cb-d1df7c44d5d4
            'to_user': HiddenInput(attrs={'required': False}),
            'content': HiddenInput(attrs={'required': False, 'value':'image'}),
            # 'image':ImageField(),
        }

class UserSignupForm(RegistrationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        email_field = User.get_email_field_name()
        print("email_field:", email_field)
        self.fields[email_field].required = False
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs.update({'autofocus': True, 
                'class':'form-control', 'placeholder':_('username')})
        self.fields['password1'].widget.attrs.update({'class':'form-control', 
            'placeholder':_('password')})
        self.fields['password2'].widget.attrs.update({'class':'form-control', 
            'placeholder':_('password')})
        self.fields[User.get_email_field_name()].widget.attrs.update({'class':'form-control',
            'placeholder':_('email address')})
        # the below code doesnot work
    # class Meta(RegistrationForm.Meta):
    #     widgets = {
    #         User.USERNAME_FIELD: forms.TextInput(attrs={'class':'form-control'}),
    #         User.get_email_field_name(): forms.EmailInput(attrs={'class':'form-control'}),
    #         'password1': forms.PasswordInput(attrs={'class':'form-control'}),
    #         'password2': forms.PasswordInput(attrs={'class':'form-control'}),
    #     }
    def save(self):
        self.instance.user_image = get_default_avatar_image()
        return super().save()

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'autofocus': True, 
                'class':'form-control', 'placeholder':_('username')})
        self.fields['password'].widget.attrs.update({ 
                'class':'form-control', 'placeholder':_('password')})

class UpdateRoomForm(ModelForm):
    error_messages = {
        'invalid_code': _(
            "Please enter a valid %(invite_code)s that min_length is 8."
        ),
        'invalid_answer': _("your answer is empty, Please enter a answer."),
        'invalid_manager':_("you has no permission to update the chatgroup info."),
    }

    def __init__(self, join_user, *args, **kwargs):
        self.manager = join_user
        super().__init__(*args, **kwargs)
        # it works like below.
        self.fields['members'].queryset = self.instance.members.all()
        self.fields['manager'].queryset = self.instance.members.all()
        self.fields['invite_time'].disabled = True
        if self.instance:
            self.instance.check_opening_status()
        self.need_check_invite_time = None
        # self.fields['members'].choices = ((1, 'abc'), (2, 'xyz'))
        # it does not work like below ,because widget is a lazy instance
        # self._meta.widgets['members'].choices = ((1,'admin'),(2, 'bill'))

    class Meta:
        model = ChatGroup
        fields = ('group_uuid', 'group_name', 'group_info', 'manager', 'members', 
                  'invite_code', 'join_deltatime', 'invite_time', 'is_opening')
        widgets = {
            'group_uuid':forms.HiddenInput(),
            'group_name':forms.TextInput(attrs={'class':'form-control'}),
            'group_info':forms.Textarea(attrs={'class':'form-control', 'rows':2}),
            'invite_code':forms.TextInput(attrs={'class':'form-control'}),
            'join_deltatime':forms.TextInput(attrs={'class':'form-control'}),
            'manager':forms.Select(attrs={'class':'form-control', }),
            'members':forms.SelectMultiple(attrs={'class':'form-control', }),
            'invite_time':forms.DateTimeInput(attrs={'class':'form-control'}),
            'is_opening':forms.CheckboxInput(),
        }

    def clean_invite_code(self):
        invite_code = self.cleaned_data.get('invite_code')
        # if self.cleaned_data.get('checkin_method') == CHECKIN_TAGS.IC:
        if len(invite_code) < 8:
            raise self.get_invalid_error('invalid_code', 'invite_code')
        return invite_code

    def clean(self):
        is_opening = self.cleaned_data['is_opening']
        if (is_opening and not self.instance.is_opening) or self.need_check_invite_time: 
            self.cleaned_data['invite_time'] = timezone.now() + self.cleaned_data['join_deltatime']
            if self.cleaned_data['invite_time'] > self.instance.delete_time:
                self.cleaned_data['invite_time'] = self.instance.delete_time
        elif not is_opening and self.instance.is_opening:
            self.cleaned_data['invite_time'] = timezone.now()
            self.cleaned_data['join_deltatime'] = timedelta()
        return self.cleaned_data

    def clean_join_deltatime(self):
        try:
            dtime = self.cleaned_data['join_deltatime']
        except:
            dtime = timedelta(minutes=settings.DEFAULT_JOIN_DELTA_TIME)
        if dtime == timedelta():
            dtime = timedelta(minutes=settings.DEFAULT_JOIN_DELTA_TIME)
        if self.data['join_deltatime'] != self.data['initial-join_deltatime']:
            self.need_check_invite_time = True
        if self.need_check_invite_time == False:
            return dtime
        # if self.instance.delete_time == None:
        #     self.instance.delete_time = self.instance.create_time + delta
        # print(self.instance.create_time.replace(tzinfo=None),self.instance.delete_time, timezone.now(), datetime.now())
        limit = self.instance.delete_time - timezone.now()
        if dtime > limit:
            dtime = limit
        return dtime

    def clean_members(self):
        members = self.cleaned_data['members']
        try:
            m = self.cleaned_data['manager'] 
        except KeyError:
            m = self.instance.manager
        members.union(User.objects.filter(pk=m.id))
        return members

    # def clean_join_answer(self):
    #     answer = self.cleaned_data.get('join_answer')
    #     if self.cleaned_data.get('checkin_method') == CHECKIN_TAGS.QA:
    #         if len(answer) < 1:
    #             raise self.get_invalid_error('invalid_answer', 'join_answer')
    #     return answer

    def get_invalid_error(self, error_name, error_field_name):
        error_field = ChatGroup._meta.get_field(error_field_name)
        print('verbose_name:', error_field.verbose_name)
        return forms.ValidationError(
            self.error_messages[error_name],
            code=error_name,
            params={error_field_name: error_field.verbose_name},
        )