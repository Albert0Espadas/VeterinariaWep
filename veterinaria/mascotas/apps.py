from django.apps import AppConfig


class MascotasConfig(AppConfig):
    # Aunque el nombre del app sea `mascotas`, aqui vive gran parte del dominio:
    # clientes, mascotas, citas, pendientes, ventas y roles visibles desde vistas.
    # Por eso esta app actua como nucleo funcional del sistema AnaVet.
    name = 'mascotas'
