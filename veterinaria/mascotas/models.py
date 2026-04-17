# models.py
from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    class Meta:
        db_table = "anavet_clientes"

    def __str__(self):
        return self.nombre


class Mascota(models.Model):
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50)
    raza = models.CharField(max_length=100)
    edad = models.IntegerField()

    dueno = models.ForeignKey(Cliente, on_delete=models.CASCADE)

    class Meta:
        db_table = "anavet_mascotas"

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE)
    fecha = models.DateTimeField()
    motivo = models.CharField(max_length=200)

    class Meta:
        db_table = "anavet_citas"

    def __str__(self):
        return f"{self.mascota.nombre} - {self.fecha}"


class Pendiente(models.Model):
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    completado = models.BooleanField(default=False)

    class Meta:
        db_table = "anavet_pendientes"

    def __str__(self):
        return self.titulo
    
class Venta(models.Model):
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "anavet_ventas"

    def __str__(self):
        return f"Venta #{self.id} - {self.total}"
