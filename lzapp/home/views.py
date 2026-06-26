from django.shortcuts import render

def main(resquet):
    return render(resquet, "masterpage.html")

def user(request):
    return render(request, "users.html")

def client(request):
    return render(request, "clients.html")