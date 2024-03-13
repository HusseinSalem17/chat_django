#   python manage.py runserver 0.0.0.0:8000
#   python manage.py migrate --run-syncdb

from concurrent.futures import thread
from rich.console import Console
console = Console(style='bold green')
import re, json
from django.shortcuts import render, redirect
from .models import Message, UserSetting, Thread
from .managers import ThreadManager
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

def email_valid(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(re.fullmatch(regex, email)): return True
    return False

@login_required
def api_online_users(request, id=0):
    users_json = {}
    
    if id != 0:
        user = User.objects.get(id=id)
        user_settings = UserSetting.objects.get(user=user)
        users_json['user'] = get_dictionary(user, user_settings)

    else:
        all_users = User.objects.all().exclude(username=request.user)
        for user in all_users:
            user_settings = UserSetting.objects.get(user=user)
            users_json[user.id] = get_dictionary(user, user_settings)

    return HttpResponse(
        json.dumps(users_json),
        content_type = 'application/javascript; charset=utf8'
    )
def get_dictionary(user, user_settings):
    return  {
                'id': user.id,
                'username': user_settings.username,
                'profile-image': user_settings.profile_image.url,
                'is-online': user_settings.is_online
            }

@login_required
def api_chat_messages(request, id):
    messages_json = {}
    count = int(request.GET.get('count', 0))
    
    thread_name =  ThreadManager.get_pair('self', request.user.id, id)
    thread = Thread.objects.get(name=thread_name)
    messages = Message.objects.filter(thread=thread).order_by('-id')
    
    for i, message in enumerate(messages, start=1):
        messages_json[message.id] = {
            'sender': message.sender.id,
            'text': message.text,
            'timestamp': message.created_at.isoformat(),
            'isread': message.isread,
        }
        if i == count: break


    return HttpResponse(
        json.dumps(messages_json),
        content_type = 'application/javascript; charset=utf8'
    )

@login_required
def api_unread(request):
    messages_json = {}
    
    user = request.user
    threads = Thread.objects.filter(users=user)
    for i, thread in enumerate(threads):
        if(user == thread.users.first()): 
            sender = thread.users.last()
            unread = thread.unread_by_1
        else: 
            sender = thread.users.first()
            unread = thread.unread_by_2
        
        messages_json[i] = {
            'sender': sender.id,
            'count': unread,
        }

    return HttpResponse(
        json.dumps(messages_json),
        content_type = 'application/javascript; charset=utf8'
    )

@login_required
def index(request, id=0):
    try:
        user = User.objects.get(username=request.user)
        Usettings = UserSetting.objects.get(user=user)

        context = {
            "settings" : Usettings,
            'id' : id,
        }
        return render(request, 'index.html', context=context)
    except User.DoesNotExist:
        # Handle the case when the user does not exist
        # You can redirect to an error page or return an error response
        return HttpResponse("User does not exist")
    except UserSetting.DoesNotExist:
        # Handle the case when the user settings do not exist
        # You can redirect to an error page or return an error response
        return HttpResponse("User settings do not exist")
    except Exception as e:
        # Handle any other exceptions that may occur
        # You can log the error or return an error response
        return HttpResponse(f"An error occurred: {str(e)}")


def login_view(request):
    logout(request)
    context = {}


    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        
        user = authenticate(username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('/')
        else:
            context = {
            "error": 'Email or Password was wrong.',
            }    
        
    return render(request, 'login.html',context)


def signup_view(request):
    logout(request)


    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        error = ''
        
        if not email_valid(email):
            error = "Wrong email address."
        try:
            if User.objects.get(username=email) is not None:
                error = 'This email is already used.'
        except: pass

        if error:  return render(request, "signup.html", context={'error': error})

        user = User.objects.create_user(
            username = email, 
            password = password,
        )
        userset = UserSetting.objects.create(user=user, username=username)
        
        login(request, user)
        return redirect('/')


    return render(request, 'signup.html')

@login_required
def settings_view(request):
    user = User.objects.get(username=request.user)
    Usettings = UserSetting.objects.get(user=user)  

    if request.method == 'POST':
        try:    avatar = request.FILES["avatar"]
        except: avatar = None
        username = request.POST['username']

        Usettings.username = username
        if(avatar != None):
            Usettings.profile_image.delete(save=True)
            Usettings.profile_image = avatar
        Usettings.save()

    context = {
        "settings" : Usettings,
        'user' : user,
    }
    return render(request, 'settings.html', context=context)