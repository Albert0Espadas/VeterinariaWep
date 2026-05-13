# models.py
from django.db import models

class Cliente(models.Model):
    # Cliente representa al propietario. No es la mascota ni la consulta:
    # es la persona base desde la que se cuelgan una o varias mascotas.
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    class Meta:
        db_table = "anavet_clientes"

    def __str__(self):
        return self.nombre


class Mascota(models.Model):
    # Mascota es el paciente clinico del sistema.
    # Esta clase se conecta con Cliente por medio de la llave foranea `dueno`.
    # Gracias a eso, un mismo cliente puede tener varias mascotas, pero cada
    # mascota sigue conservando su propio ID e historial individual.
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50)
    raza = models.CharField(max_length=100)
    edad = models.IntegerField()

    # Varias mascotas pueden pertenecer al mismo cliente.
    dueno = models.ForeignKey(Cliente, on_delete=models.CASCADE)

    class Meta:
        db_table = "anavet_mascotas"

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    # Cita es el punto donde se une la agenda con el expediente clinico.
    # Se conecta directamente con Mascota, no con Cliente, porque el historial
    # debe pertenecer a un paciente concreto aunque el dueno tenga varias mascotas.
    # Desde esta clase luego se puede recuperar al dueno siguiendo:
    # cita -> mascota -> dueno
    # Cada cita pertenece a una mascota especifica.
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE)
    # `fecha` es la referencia de agenda que usan calendario, dashboard y consultas.
    fecha = models.DateTimeField()
    # `motivo` resume por que entra esa consulta o cita al sistema.
    motivo = models.CharField(max_length=200)
    # Aqui se guarda la nota clinica escrita por veterinaria.
    notas_medicas = models.TextField(blank=True, default="")

    class Meta:
        db_table = "anavet_citas"

    def __str__(self):
        return f"{self.mascota.nombre} - {self.fecha}"


class Pendiente(models.Model):
    # Pendiente no pertenece al flujo medico directo; funciona como apoyo
    # operativo interno para recepcion, dashboard y seguimiento administrativo.
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    completado = models.BooleanField(default=False)

    class Meta:
        db_table = "anavet_pendientes"

    def __str__(self):
        return self.titulo

class Venta(models.Model):
    # Venta representa el modulo comercial o de caja.
    # No se conecta por llave foranea con Cliente o Mascota en esta version,
    # asi que hoy se usa como registro independiente de cobro.
    # Si mas adelante quieren tickets asociados a un paciente, esta seria la
    # clase natural para extender esa relacion.
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    # `total` es el importe final cobrado en la operacion.
    total = models.DecimalField(max_digits=10, decimal_places=2)
    # `metodo_pago` decide la logica de cobro y el comportamiento del cambio.
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    # `monto_pagado` es lo recibido del cliente en caja.
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    # Cambio aplica solo cuando el metodo es efectivo.
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # `fecha` se llena sola para construir reportes del dia y ventas recientes.
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "anavet_ventas"

    def __str__(self):
        return f"Venta #{self.id} - {self.total}"
