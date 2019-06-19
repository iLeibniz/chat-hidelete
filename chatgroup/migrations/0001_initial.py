# Generated by Django 2.2 on 2019-06-09 12:23

import chatgroup.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatGroup',
            fields=[
                ('group_uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, verbose_name='group UUID')),
                ('group_image', models.CharField(blank=True, max_length=100, null=True)),
                ('group_name', models.CharField(max_length=30, verbose_name='group name')),
                ('group_info', models.TextField(blank=True, default=chatgroup.models.get_default_info, null=True, verbose_name='group info')),
                ('checkin_method', models.PositiveSmallIntegerField(choices=[(0, 'annonyment join'), (1, 'use invite_code'), (2, 'use question and answer')], default=1)),
                ('invite_code', models.CharField(default=chatgroup.models.get_default_invite_code, max_length=30)),
                ('join_question', models.CharField(blank=True, default='', max_length=150, verbose_name='please input a question to join')),
                ('join_answer', models.CharField(blank=True, default='', max_length=150, verbose_name='please answer the question to join')),
                ('join_deltatime', models.DurationField(default=chatgroup.models.get_default_timedelta, verbose_name='open time')),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='group created time')),
                ('invite_time', models.DateTimeField(blank=True, null=True, verbose_name='Accept joinment until')),
                ('delete_time', models.DateTimeField(blank=True, null=True, verbose_name='when to delete the group')),
                ('is_opening', models.BooleanField(default=True, verbose_name='open inviting?')),
                ('manager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chatgroups', to=settings.AUTH_USER_MODEL)),
                ('members', models.ManyToManyField(related_name='user_joined_groups', to=settings.AUTH_USER_MODEL, verbose_name='members')),
            ],
            options={
                'verbose_name': 'Chat Group',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('msg_type', models.PositiveSmallIntegerField(choices=[(1, 'TEXT'), (2, 'IMAGE'), (3, 'VIDEO'), (4, 'FILE')], default=2, verbose_name='message type')),
                ('content', models.TextField(default='', verbose_name='')),
                ('send_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='send time')),
                ('image', models.ImageField(blank=True, default=None, null=True, upload_to='images/', verbose_name='image')),
                ('video', models.FileField(blank=True, default=None, null=True, upload_to='videos/', verbose_name='video')),
                ('file', models.FileField(blank=True, default=None, null=True, upload_to='files/', verbose_name='file')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_sended_msgs', to=settings.AUTH_USER_MODEL, verbose_name='message sended from user')),
                ('to_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_received_msgs', to='chatgroup.ChatGroup', verbose_name='send message to group')),
                ('to_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_received_msgs', to=settings.AUTH_USER_MODEL, verbose_name='send message to user')),
            ],
            options={
                'verbose_name': 'Message',
            },
        ),
    ]