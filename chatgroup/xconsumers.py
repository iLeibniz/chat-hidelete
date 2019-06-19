# chat/consumers.py
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json, traceback
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from chatgroup.models import ChatGroup
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.conf import settings
from channels.generic.websocket import JsonWebsocketConsumer
from chatgroup.exceptions import ClientError
from chatgroup.utils import get_room_or_error
from chatgroup.models import Message
import json
from pprint import pprint

WS_TOKEN = get_random_string()
User = get_user_model()
MSG_TYPE_CHOICES = dict(Message.MSG_TYPE_CHOICES)

class ChatConsumer(JsonWebsocketConsumer):
    """
    This chat consumer handles websocket connections for chat clients.

    It uses JsonWebsocketConsumer, which means all the handling functions
    must be functions, and any sync work (like ORM access) has to be
    behind database_sync_to_or sync_to_async. For more, read
    http://channels.readthedocs.io/en/latest/topics/consumers.html
    """

    ##### WebSocket event handlers

    def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # Are they logged in?
        # ws_token = self.scope['url_route']['kwargs']['ws_token']
        if self.scope["user"].is_anonymous:
            # Reject the connection
            print("is_anonymous")
            self.close()
        else:
            print("accepted.")
            # Accept the connection
            self.accept()
        # Store which rooms the user has joined on this connection
        self.rooms = set()
        self.send_json({
            'command':'heart_beat',
            'message':'need relink server',
            })

    def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        # print("recieve content>>>>>>>>>>>>>>>:\n",content,"\n>>>>>>>>>>>>>>>>>>>>>>>>>>")
        command = content.get("command", None)
        # print(command, self.rooms, self.scope["user"].username)
        try:
            if command == "join":
                # Make them join the room
                self.join_room(content["gid"])
            elif command == "leave":
                # Leave the room
                self.leave_room(content["gid"], content['roomname'], content['need_notify'])
            elif command == "send":
                self.send_room(content["gid"], content)
            elif command == "heart_beat":
                self.send_link_echo(content)
            elif command == "remove":
                self.send_remove(content['gid'], content['remove_users'], content['roomname'])
            elif command == "flag_time":
                if not self.scope["user"].is_anonymous:
                    self.scope['user'].save()
        except ClientError as e:
            # Catch any errors and send it back
            print(e.code)
            self.send_json({"error": e.code})

    def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave all the rooms we are still in
        for room_id in list(self.rooms):
            try:
                self.leave_room(room_id)
            except ClientError:
                pass
        if not self.scope["user"].is_anonymous:
            self.scope['user'].save()
        # print("when %s disconnect, last_date_wsonline:%s"%(self.scope['user'].username, self.scope['user'].last_date_wsonline))

    def get_members(self, room_id):
        try:
            members = ChatGroup.objects.get(group_uuid=room_id).members.all()
            members = len(members)
        except ChatGroup.DoesNotExist:
            members = 0
        return members

    ##### Command helper methods called by receive_json
    def join_room(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        room = get_room_or_error(room_id, self.scope["user"])
        if room_id in self.rooms: return
        
        # Send a join message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            async_to_sync(self.channel_layer.group_send)(
                "room_"+str(room.group_uuid),
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "group_name": room.group_name,
                    "group_image": room.group_image,
                    "username": self.scope["user"].username,
                    "command": "join_newer",
                    "uid":self.scope['user'].id,
                    "members": self.get_members(room_id),
                }
            )
        # Store that we're in the room
        self.rooms.add(room_id)
        # Add them to the group so they get room messages
        async_to_sync(self.channel_layer.group_add)(
            "room_"+str(room.group_uuid),
            self.channel_name,
        )
        # Instruct their client to finish opening the room
        self.send_json({
            "room_id": room_id,
            "roomname": room.group_name,
            "group_image": room.group_image,
            "username": "You",
            "command": "join_echo",
            "uid":self.scope['user'].id,
            "members": self.get_members(room_id),
        })
        time_until = timezone.now()
        return self.push_latest_unread_messages(room, time_until)

    def push_latest_unread_messages(self, room, time_until):
        start_time = self.scope['user'].last_date_wsonline or timezone.now()
        qset = Message.objects.filter(send_time__gte = start_time, to_group = room).exclude(from_user = self.scope['user'])
        if qset:
            qset = qset.order_by('send_time')
            for obj in qset.all():
                # print(obj.__dict__)
                file = obj.image or obj.video or obj.file
                fileurl = filename = filesize = None
                if file:
                    fileurl = file.url
                    filename = fileurl.split('/')[-1]
                    filesize = file.size
                if obj.image:
                    msgImgDataUrl = "/static/"+obj.image.url
                else:
                    msgImgDataUrl = "/static/chat/video_default_image.png"
                try:
                    fromUserImgUrl = "/static/"+obj.from_user.user_image
                except:
                    fromUserImgUrl =  "/static/avatar/default7.jpg"
                data = {
                        "gid": str(obj.to_group.group_uuid),
                        "msg_type": MSG_TYPE_CHOICES[obj.msg_type].lower(),
                        "uid": obj.from_user.id,
                        "touid": obj.to_user.id if obj.to_user else '',
                        "fromUserName":obj.from_user.username,
                        "msgContent":obj.content,
                        "toMe":False,
                        "fromUserImgUrl": fromUserImgUrl,
                        "msgImgDataUrl":msgImgDataUrl,
                        "msgFileSize": filesize,
                        "msgFileName": filename,
                        "msgFileUrl": fileurl,
                    }
                self.send_json({
                    "command": "unread_message",
                    "content": data,
                    })
        if len(self.rooms) == self.scope['user'].user_joined_groups.count():
            self.scope['user'].save()


    def leave_room(self, room_id, roomname="", need_notify=True):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        # room = get_room_or_error(room_id, self.scope["user"])
        # Send a leave message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS and need_notify:
            async_to_sync(self.channel_layer.group_send)(
                "room_"+str(room_id),
                {
                    "type": "chat.leave",
                    "room_id": room_id,
                    "roomname": roomname,
                    "username": self.scope["user"].username,
                    "uid": self.scope["user"].id,
                    "members": self.get_members(room_id),
                    "command": "leave_group",
                }
            )
        # Remove that we're in the room
        self.rooms.discard(room_id)
        # Remove them from the group so they no longer get room messages
        async_to_sync(self.channel_layer.group_discard)(
            "room_"+str(room_id),
            self.channel_name,
        )
        # Instruct their client to finish closing the room
        self.send_json({
            "room_id": room_id,
            "command": "leave_echo",
        })

    def send_remove(self, room_id, remove_users, roomname):
        members = self.get_members(room_id)
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            async_to_sync(self.channel_layer.group_send)(
                'room_'+str(room_id),
                {
                    "type":"chat.remove",
                    "room_id":room_id,
                    "roomname":roomname,
                    "remove_users": remove_users,
                    "members": members,
                    "command": "remove_users",
                })
        self.send_json({
            "room_id": room_id,
            "roomname":roomname,
            "remove_users": remove_users,
            "members": members,
            "command": "remove_echo",
        })

    def send_link_echo(self, content):
        # print("rooms:", self.rooms)
        # Check they are in this room
        if len(self.rooms) == 0:
            raise ClientError("ROOM_ACCESS_DENIED")
        self.send_json({
            'command':'link_echo',
            'content':content,
        })


    def send_room(self, room_id, message):
        """
        Called by receive_json when someone sends a message to a room.
        """
        # print("rooms:", self.rooms)
        # Check they are in this room
        if room_id not in self.rooms:
            # self.join_room(room_id)
            raise ClientError("ROOM_ACCESS_DENIED")

        # Get the room and send to the group about it
        room = get_room_or_error(room_id, self.scope["user"])
        # print("send_room message:\n", message)
        async_to_sync(self.channel_layer.group_send)(
            "room_"+str(room.group_uuid),
            {
                "type": "chat.message",
                "room_id": room_id,
                "username": self.scope["user"].username,
                "uid": self.scope["user"].id,
                "content": message,
                "command": "message",
            }
        )

    ##### Handlers for messages sent over the channel layer

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    def chat_join(self, event):
        """
        Called when someone has joined our chat.
        """
        # Send a message down to the client
        # print("join event:\n", event)
        self.send_json(
            {
                "room_id": event["room_id"],
                "roomname": event["group_name"],
                "username": event["username"],
                "uid": event["uid"],
                "members": event["members"],
                "command": event["command"],
            },
        )

    def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        # print("leave event:\n", event)
        self.send_json(
            {
                "room_id": event["room_id"],
                "roomname": event["roomname"],
                "username": event["username"],
                "uid": event["uid"],
                "members": event["members"],
                "command": event["command"],
            },
        )
    
    def chat_remove(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        # print("remove event:\n", event)
        self.send_json(
            {
                "room_id": event["room_id"],
                "roomname": event["roomname"],
                "members": event["members"],
                "remove_users": event["remove_users"],
                "command": event["command"],
            },
        )
    def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        # print("message event:\n", event)
        self.send_json(
            {
                "room_id": event["room_id"],
                "username": event["username"],
                "uid": event['uid'],
                "content": event["content"],
                "command": event["command"],
            },
        )
