from django.urls import path
from . import views

urlpatterns = [
    path('Lview',views.Lview,name="Lview"),
    path('Rview',views.Rview,name="Rview"),
    path('Review',views.Review,name="Review"),
]
