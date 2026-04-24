from django.contrib import admin
from django.urls import path

from mascotas import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ping/", views.ping, name="ping"),
    path("", views.login_view, name="login"),
    path("registro/", views.registro_view, name="registro"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("recepcion/", views.recepcion, name="recepcion"),
    path("pos/", views.punto_venta, name="pos"),
    path("consultas/", views.consultas, name="consultas"),
    path("citas/", views.citas, name="citas"),
    path("logout/", views.logout_view, name="logout"),
    path("crear-cita/", views.crear_cita, name="crear_cita"),
    path("completar/<int:id>/", views.completar_pendiente, name="completar"),
    path("eliminar/<int:id>/", views.eliminar_pendiente, name="eliminar"),
    path("cliente/<int:id>/eliminar/", views.eliminar_cliente, name="eliminar_cliente"),
    path("cliente/<int:id>/editar/", views.editar_cliente, name="editar_cliente"),
    path("mascota/<int:id>/eliminar/", views.eliminar_mascota, name="eliminar_mascota"),
    path("mascota/<int:id>/editar/", views.editar_mascota, name="editar_mascota"),
]