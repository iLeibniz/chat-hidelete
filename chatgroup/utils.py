
import functools
import uuid, os
from django.conf import settings
from chatgroup.models import ChatGroup
from django.shortcuts import redirect
from django.db.models import Model
from django.core.files.base import File
from django.db.models.fields.files import FieldFile
from pprint import pprint
from chatgroup.exceptions import ClientError
from chatgroup.models import ChatGroup

def uuid_or_redirect(key='pk', to_url='/'):
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self, request, *args, **kwargs):
            value = kwargs.get(key)
            if isinstance(value, str):
                try:
                    self.chatroom_id = uuid.UUID(value)
                    self.chatgroup = ChatGroup.objects.get(pk = self.chatroom_id)
                    self.chatgroup.check_opening_status()
                except ValueError as e:
                    print('ValueError error raised, classname is :', type(e))
                    if request.is_ajax():
                        kwargs.update({key:value, 'iderror':'chatroom id is wrong', 'command':None})
                        return self.get_ajax(request, status=400, **kwargs)
                    return redirect(to_url)
                except ChatGroup.DoesNotExist as e:
                    print('ChatGroup DoesNotExist error raised, classname is :', type(e))
                    if request.is_ajax():
                        kwargs.update({key:value, 'iderror':'chatroom id does not exist', 'command':'remove'})
                        return self.get_ajax(request, status=400, **kwargs)
                    return redirect(to_url)
            else:
                print("function:%s, kwargs['%s'] is not str."%(func, key))
                return redirect(to_url)
            return func(self, request, *args, **kwargs)
        return wrapped
    return decorator

def object_to_dict(obj):
    if obj == None:
            return None
    if isinstance(obj, Model):
        # pprint(obj.__dict__)
        obj = obj.__dict__.copy()
        for k,v in obj.items():
            if isinstance(v, Model):
                obj[k] = object_to_dict(v)
            # set InMemoryTemproryFile.None type to None
            if isinstance(v, FieldFile) and v == None:
                obj[k] = None
            if k.startswith('_'):
                obj[k] = k
            if isinstance(v, list):
                obj[k] = len(v)
    print(obj)
    return obj

def object2AttrDict(obj): 
    res = {} 
    for attr_name in dir(obj):
        try:
            attr = getattr(obj, attr_name)
            if callable(attr): # method
                continue 
        except AttributeError:
            continue
        res[attr_name] = attr
    return res

def model2Json(obj):
    attrs = object2AttrDict(obj)
    res = {}
    for attr_name, attr in attrs.items():
        if str(attr_name).startswith("_") or attr_name == "pk":
            continue
        res[attr_name] = attr
    return res



# This decorator turns this function from a synchronous function into an async one
# we can call from our async consumers, that handles Django DBs correctly.
# For more, see http://channels.readthedocs.io/en/latest/topics/databases.html
def get_room_or_error(room_id, user):
    """
    Tries to fetch a room for the user, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        room = ChatGroup.objects.get(group_uuid=room_id)
    except ChatGroup.DoesNotExist:
        raise ClientError("ROOM_INVALID")
    # Check permissions
    # if room.staff_only and not user.is_staff:
    #     raise ClientError("ROOM_ACCESS_DENIED")
    if user not in room.members.all():
        raise ClientError("USER_HAS_BEEN_DENYED")
    return room

def create_avator_list(file_dir, ext=".jpg", base="avatar/"):
    # print(file_dir)
    lis = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == ext:
                lis.append(base+file)
    return lis, len(lis)

AVATAR_LIST, AVATAR_LEN = create_avator_list(settings.BASE_DIR+"\\upload\\avatar\\")
# print(AVATAR_LIST, AVATAR_LEN)