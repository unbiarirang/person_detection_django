import base64
import io
import cv2
import time
import os

from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import StreamingHttpResponse,HttpResponse
from django.views.decorators import gzip
from django.template import Context, loader
from django.contrib import auth
from django.contrib.auth.models import User
from django import forms
from .models import Record
from .forms import changeform,userform,warningform
from darkflow.net.build import TFNet


def remove_record(request):
    id = request.GET.get("id")
    Record.objects.filter(id = id).delete()
    Records = Record.objects.filter(date__lte=timezone.now()).order_by('-date')
    return render(request, 'warning_record.html',{'Records': Records})

def warning_record(request):
    Records = Record.objects.filter(date__lte=timezone.now()).order_by('-date')
    return render(request, 'warning_record.html',{'Records': Records})

pl1 = 998
pl2 = 999
t1 = -1
t2 = -1
def detection(request):
    if request.method == "POST":
        form = warningform(request.POST)
        if form.is_valid():
            Tphase1 = form.cleaned_data.get('Tphase1')
            Tphase2 = form.cleaned_data.get('Tphase2')
            Pphase1 = form.cleaned_data.get('Pphase1')
            Pphase2 = form.cleaned_data.get('Pphase2')
            global pl1
            global pl2
            global t1
            global t2
            if int(Pphase1) >= 0 and int(Pphase2) >= 0:
                pl1 = Pphase1
                pl2 = Pphase2
            else:
                pl1 = 998
                pl2 = 999
            t1 = Tphase1
            t2 = Tphase2
    
            return redirect('/')
    else:
        form = warningform()
        return render(request, 'detection.html',{'form': form})

def change_password(request):
    if request.method == "POST":
        form = changeform(request.POST)
        if form.is_valid():
            Username = request.user.username
            Oldpassword = form.cleaned_data.get('Oldpassword')
            Newpassword = form.cleaned_data.get('Newpassword')
            Confirmpass = form.cleaned_data.get('Confirmpass')
            user = auth.authenticate(username=Username, password=Oldpassword)
            if user is not None and Confirmpass == Newpassword:
                user.set_password(Newpassword)
                user.save()
                return redirect('/')
            else:
                message = 'Oldpassword is wrong or new password is different'
                return render(request,'change_password.html',{'message':message})
    else:
        form = changeform()
        return render(request, 'change_password.html', {'form': form})
    
def add_user(request):  
    if request.method == 'POST':
        form = userform(request.POST)  
        if form.is_valid():
            Username = form.cleaned_data['Username']
            Password = form.cleaned_data['Password']
            Confirmpass = form.cleaned_data['Confirmpass']
            if User.objects.filter(username=Username) or Confirmpass != Password:
               message = 'Username already exists or password is different'
               return render(request, 'add_user.html',{'message':message})

            user = User.objects.create_user(username=Username, password=Password)
            user.save()
            return redirect('/')    
    else:
        form = UserCreationForm()
    return render(request, 'add_user.html',{'form': form})

def display(request):
    img_str = base64.b64encode(b"")
    
    return render(request, 'post_list.html', {'img_str': img_str})

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
    def __del__(self):
        self.video.release()

    def get_frame(self):
        _, image = self.video.read()
        _, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield(b'--frame\r\n'
        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

# @gzip.gzip_page
def detect(request):
    return StreamingHttpResponse(run_darkflow(), content_type="multipart/x-mixed-replace;boundary=frame")

def run_darkflow():
    options = {
                "model": "./cfg/v1.1/tiny-yolov1.cfg",
                "load": "./bin/tiny-yolo-v1.1.weights",
                "threshold": 0.1,
                "demo": "camera",
            }

    tfnet = TFNet(options)
    return tfnet.camera(pl1,pl2,t1,t2)