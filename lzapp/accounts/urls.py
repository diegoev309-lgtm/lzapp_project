from django.urls import path
from accounts.views import Lview, Rview, Review

urlpatterns = [
    path('Lview',Lview,name="Lview"),
    path('Rview',Rview,name="Rview"),
    path('Review',Review,name="Review"),
]
