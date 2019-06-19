from datetime import datetime, timedelta
from django.utils import timezone
from django.utils import duration, crypto
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db import models
import uuid
from collections import namedtuple
from django.urls import reverse
from django.conf import settings

User = get_user_model()

delta = timedelta(days = settings.GROUP_LIFE_DATES)
CheckinTags = namedtuple('CheckinTags', ['AJ', 'IC', 'QA'])
CHECKIN_TAGS = CheckinTags(0, 1, 2)
join_delta = timedelta(minutes=settings.DEFAULT_JOIN_DELTA_TIME)

def get_default_avatar_image():
    return AVATAR_LIST[random.randint(0, AVATAR_LEN)]

def get_default_timedelta():
    # maybe based on a old db, when use duration, it must to new a timedelta instance with all the kwarguments.
    # if not ,raise str object has not days error
    return join_delta

def get_default_invite_code():
    # return "11111111"
    return crypto.get_random_string(8, allowed_chars="ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678")

def get_default_info():
    return _("Click chatroom image to show the chatroom's profile as you build it.")

class ChatGroup(models.Model):
    CHECKIN_METHODS = (
        (0, _('annonyment join')),
        (1, _('use invite_code')),
        (2, _('use question and answer')),
    )

    group_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_('group uuid'))
    group_image = models.CharField(max_length=100)
    group_name = models.CharField(max_length=30, verbose_name=_('group_name'))
    group_info = models.TextField(default=get_default_info,null=True, blank=True, verbose_name=_('group_info'))
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatgroups', verbose_name=_('manager'))
    members = models.ManyToManyField(User, verbose_name=_('members'), related_name='user_joined_groups')
    checkin_method = models.PositiveSmallIntegerField(choices=CHECKIN_METHODS, default=1, verbose_name=_('checkin_method'))
    invite_code = models.CharField(max_length=30, default=get_default_invite_code, verbose_name=_('invite_code'))
    join_question = models.CharField(max_length=150, default='', blank=True, verbose_name='please input a question to join')
    join_answer = models.CharField(max_length=150, default='', blank=True, verbose_name='please answer the question to join')
    join_deltatime = models.DurationField(default=get_default_timedelta, verbose_name=_("join_deltatime"))
    create_time = models.DateTimeField(default=timezone.now, verbose_name='group created time')
    invite_time = models.DateTimeField(null=True, blank=True, verbose_name=_('Accept joinment until'))
    delete_time = models.DateTimeField(null=True, blank=True, verbose_name='when to delete the group')
    is_opening = models.BooleanField(default=True, verbose_name=_('open inviting?'))
    # capcha reserved

    def __str__(self):
        return self.group_name

    def get_absolute_url(self):
        return reverse('channelsroom', kwargs=dict(pk=self.pk))

    class Meta:
        verbose_name = 'Chat Group'

    def check_passport(self, invite_code=None, join_answer=None):
        if self.checkin_method == CHECKIN_TAGS.AJ: return True
        elif self.checkin_method == CHECKIN_TAGS.IC:
            if self.invite_code == invite_code: return True
        elif self.checkin_method == CHECKIN_TAGS.QA:
            if self.join_answer == join_answer: return True
        return False

    def get_verbose_code(self):
        return self.CHECKIN_METHODS[self.checkin_method][1]

    def change_manager(self, user, func=None):
        if not callable(func):
            func = lambda: func
        new_manager = func()
        if isinstance(new_manager, User) and user != new_manager:
            self.manager = new_manager
            return
        qset = self.members.all().order_by("date_joined").all()
        if len(qset) <= 1:
            return
        if user == qset[0]:
            new_manager = qset[1]
        else:
            new_manager = qset[0]
        self.manager = new_manager
        self.save()

    def check_opening_status(self, force = False):
        if self.is_opening == False and force == False:
            return False
        if self.invite_time == None:
            self.invite_time = timezone.now() + self.join_deltatime
            self.delete_time = timezone.now() + delta
        if timezone.now() > self.invite_time:
            self.is_opening = False
        self.save()
        return self.is_opening

class Message(models.Model):
    MSG_TYPE_CHOICES = (
        (1, 'TEXT'),
        (2, 'IMAGE'),
        (3, 'VIDEO'),
        (4, 'FILE'),
    )
    msg_type = models.PositiveSmallIntegerField(choices=MSG_TYPE_CHOICES, default=2, verbose_name='message type')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_sended_msgs',
                                  verbose_name='message sended from user')
    to_group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='group_received_msgs',
                                 verbose_name='send message to group')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_received_msgs', null=True,
                                blank=True, verbose_name='send message to user')
    content = models.TextField(default='', verbose_name='')
    send_time = models.DateTimeField(default=timezone.now, verbose_name='send time')
    image = models.ImageField(default=None, null=True, blank=True, upload_to='images/', verbose_name='image')
    video = models.FileField(default=None, null=True, blank=True, upload_to='videos/', verbose_name='video')
    file = models.FileField(default=None, null=True, blank=True, upload_to='files/', verbose_name='file')

    class Meta:
        verbose_name = 'Message'
