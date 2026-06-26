from django.urls import path
from home.views import main, user, client

urlpatterns = [
    path('main',main,name="main"),
    path('user',user,name="user"),
    path('client',client,name="client"),
]