from django.contrib import admin
from django.urls import path
from mascotas import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('completar/<int:id>/', views.completar_pendiente, name='completar'),
    path('eliminar/<int:id>/', views.eliminar_pendiente, name='eliminar'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
]
