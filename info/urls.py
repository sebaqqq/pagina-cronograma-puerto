# info/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('detalle/<int:index>/', views.detalle, name='detalle'),
]
