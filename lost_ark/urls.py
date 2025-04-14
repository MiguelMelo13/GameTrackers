from django.urls import path

from lost_ark import views

urlpatterns = [
    path('', views.home, name='home'),
]
