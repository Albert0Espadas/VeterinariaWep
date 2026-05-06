from django.contrib import admin

from .models import Cita, Cliente, Mascota, Pendiente, Venta

admin.site.register(Pendiente)
admin.site.register(Cliente)
admin.site.register(Mascota)
admin.site.register(Cita)
admin.site.register(Venta)
