from django.contrib import admin
from .models import Cliente, Mascota, Cita, Pendiente

from django.contrib import admin
from .models import Pendiente, Cita

admin.site.register(Pendiente)
admin.site.register(Cliente)
admin.site.register(Mascota)
admin.site.register(Cita)
