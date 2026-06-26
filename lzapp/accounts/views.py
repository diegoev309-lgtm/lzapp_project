from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail

#authentication del parte del usuario 

def Lview(resquet):
    return render(resquet, "login.html")

def Rview(request):
    return render(request, "regsitro.html")

def Review(request):
    return render(request, "recuperar.html")