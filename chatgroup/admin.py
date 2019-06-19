# Register your models here.

from django.contrib import admin
from chatgroup.models import ChatGroup, Message


@admin.register(ChatGroup)
class ChatGroupModelAdmin(admin.ModelAdmin):
    list_display = ('group_uuid', 'group_name', 'group_info', 'manager', 'get_members','checkin_method',
        'invite_code', "join_question", 'join_answer', 'join_deltatime', 'create_time',  'delete_time')
    list_filter = ('group_name',)

    def get_members(self, obj):
        return ','.join((u.username for u in obj.members.all()))


@admin.register(Message)
class MessageModelAdmin(admin.ModelAdmin):
    list_filter = ('msg_type', 'from_user', 'to_group', 'to_user')

    # has created a __str__() for ChatGroup Model,so to_group can display group_name in admin site
    list_display = ('msg_type', 'from_user', 'to_group', 'to_user', 'content')

    # or create a function to return a str for displaying group_name in admin site
    # list_display = ('msg_type', 'from_user', 'get_group_name', 'to_user', 'content')
    # def get_group_name(self, obj):
    #     return obj.to_group.group_name
