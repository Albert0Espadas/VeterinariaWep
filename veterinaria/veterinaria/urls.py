from django.contrib import admin
from django.urls import path
from mascotas import views

urlpatterns = [
    path('', views.login_view),
    path('login/', views.login_view, name='login'),
    path('Registro/', views.registro_view, name= 'registro'),
    path('dashboard/', views.dashboard_view, name= 'dashboard'),
]