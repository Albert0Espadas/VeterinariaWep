import json

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cita, Cliente, Mascota, Pendiente, Venta
from .roles import ROLE_ADMIN, ROLE_SECRETARIA, ROLE_VETERINARIA


class PingViewTests(TestCase):
    def test_ping_returns_ok_json(self):
        response = self.client.get(reverse("ping"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": "ok", "message": "VeterinariaWep activa"},
        )


class AuthenticatedViewsMixin(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        self.user = User.objects.create_user(username="demo", password="12345")
        self.user.groups.add(admin_group)
        self.client.login(username="demo", password="12345")


class DashboardViewTests(AuthenticatedViewsMixin):
    def test_dashboard_shows_real_metrics_and_future_appointments(self):
        cliente = Cliente.objects.create(
            nombre="Ana Perez",
            telefono="5551234567",
            email="ana@example.com",
        )
        mascota = Mascota.objects.create(
            nombre="Luna",
            especie="Perro",
            raza="Mestizo",
            edad=4,
            dueno=cliente,
        )
        Cita.objects.create(
            mascota=mascota,
            motivo="Vacunacion",
            fecha=timezone.now() + timezone.timedelta(hours=2),
        )
        Cita.objects.create(
            mascota=mascota,
            motivo="Revision",
            fecha=timezone.now() + timezone.timedelta(days=1),
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pacientes Totales")
        self.assertContains(response, "Clientes")
        self.assertContains(response, "Pendientes Activos")
        self.assertContains(response, "Proximas Citas")
        self.assertContains(response, "Nueva Cita")
        self.assertContains(response, "Luna")

    def test_complete_and_delete_pending_require_post(self):
        pendiente = Pendiente.objects.create(titulo="Llamar", descripcion="Confirmar cita")

        get_response = self.client.get(reverse("completar", args=[pendiente.id]))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse("completar", args=[pendiente.id]))
        self.assertEqual(post_response.status_code, 302)

        pendiente.refresh_from_db()
        self.assertTrue(pendiente.completado)


class CrearCitaViewTests(AuthenticatedViewsMixin):
    def test_crear_cita_returns_json_and_creates_related_records(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps(
                {
                    "mascota": "Milo",
                    "dueno": "Carla Gomez",
                    "motivo": "Desparasitacion",
                    "fecha": "2026-04-08T10:30:00",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cita.objects.count(), 1)
        self.assertEqual(Mascota.objects.count(), 1)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(Cita.objects.first().motivo, "Desparasitacion")
        self.assertEqual(Mascota.objects.first().nombre, "Milo")


class RecepcionViewTests(AuthenticatedViewsMixin):
    def test_recepcion_registers_client(self):
        response = self.client.post(
            reverse("recepcion"),
            {
                "registrar_cliente": "1",
                "nombre": "Laura Mendez",
                "telefono": "5511223344",
                "email": "laura@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(Cliente.objects.first().nombre, "Laura Mendez")

    def test_recepcion_registers_pet_with_owner(self):
        cliente = Cliente.objects.create(
            nombre="Diego",
            telefono="5512345678",
            email="diego@example.com",
        )

        response = self.client.post(
            reverse("recepcion"),
            {
                "registrar_mascota": "1",
                "nombre_mascota": "Nina",
                "especie": "Gato",
                "raza": "Criollo",
                "edad": 2,
                "cliente": cliente.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Mascota.objects.count(), 1)
        self.assertEqual(Mascota.objects.first().dueno, cliente)


class PuntoVentaViewTests(AuthenticatedViewsMixin):
    def test_pos_registers_cash_sale_and_change(self):
        response = self.client.post(
            reverse("pos"),
            {
                "total": "250.00",
                "metodo_pago": "efectivo",
                "monto_pagado": "300.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertContains(response, "Venta registrada con exito.")
        self.assertEqual(Venta.objects.first().cambio, 50)


class NewModulesViewTests(AuthenticatedViewsMixin):
    def test_consultas_page_loads(self):
        response = self.client.get(reverse("consultas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Area de Consultas")

    def test_citas_page_loads(self):
        response = self.client.get(reverse("citas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modulo de Citas")


class RoleAccessTests(TestCase):
    def setUp(self):
        self.secretaria_group, _ = Group.objects.get_or_create(name=ROLE_SECRETARIA)
        self.veterinaria_group, _ = Group.objects.get_or_create(name=ROLE_VETERINARIA)
        self.admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)

    def test_registration_assigns_secretaria_role_by_default(self):
        response = self.client.post(
            reverse("registro"),
            {
                "username": "recepcion1",
                "password": "ClaveSegura1",
                "password2": "ClaveSegura1",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="recepcion1")
        self.assertTrue(user.groups.filter(name=ROLE_SECRETARIA).exists())

    def test_veterinaria_cannot_open_recepcion(self):
        user = User.objects.create_user(username="vet", password="12345")
        user.groups.add(self.veterinaria_group)
        self.client.login(username="vet", password="12345")

        response = self.client.get(reverse("recepcion"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_secretaria_cannot_open_consultas(self):
        user = User.objects.create_user(username="sec", password="12345")
        user.groups.add(self.secretaria_group)
        self.client.login(username="sec", password="12345")

        response = self.client.get(reverse("consultas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modo Lectura")

    def test_secretaria_cannot_edit_consulta(self):
        cliente = Cliente.objects.create(
            nombre="Ana Perez",
            telefono="5551234567",
            email="ana@example.com",
        )
        mascota = Mascota.objects.create(
            nombre="Luna",
            especie="Perro",
            raza="Mestizo",
            edad=4,
            dueno=cliente,
        )
        cita = Cita.objects.create(
            mascota=mascota,
            motivo="Vacunacion",
            fecha=timezone.now() + timezone.timedelta(hours=2),
        )
        user = User.objects.create_user(username="sec2", password="12345")
        user.groups.add(self.secretaria_group)
        self.client.login(username="sec2", password="12345")

        response = self.client.post(
            reverse("consultas"),
            {
                "cita_id": cita.id,
                "motivo": "Cambio no permitido",
                "fecha": "2026-05-01T10:00",
            },
        )

        self.assertEqual(response.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.motivo, "Vacunacion")

    def test_veterinaria_can_edit_consulta(self):
        cliente = Cliente.objects.create(
            nombre="Carlos Ruiz",
            telefono="5559876543",
            email="carlos@example.com",
        )
        mascota = Mascota.objects.create(
            nombre="Nina",
            especie="Gato",
            raza="Criollo",
            edad=3,
            dueno=cliente,
        )
        cita = Cita.objects.create(
            mascota=mascota,
            motivo="Revision",
            fecha=timezone.now() + timezone.timedelta(hours=4),
        )
        user = User.objects.create_user(username="vet2", password="12345")
        user.groups.add(self.veterinaria_group)
        self.client.login(username="vet2", password="12345")

        response = self.client.post(
            reverse("consultas"),
            {
                "cita_id": cita.id,
                "motivo": "Revision completa",
                "fecha": "2026-05-01T11:30",
                "notas_medicas": "Paciente estable. Requiere seguimiento en una semana.",
            },
        )

        self.assertEqual(response.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.motivo, "Revision completa")
        self.assertEqual(cita.notas_medicas, "Paciente estable. Requiere seguimiento en una semana.")

    def test_veterinaria_can_adjust_cita_from_citas_module(self):
        cliente = Cliente.objects.create(
            nombre="Marta Leon",
            telefono="5556781234",
            email="marta@example.com",
        )
        mascota = Mascota.objects.create(
            nombre="Toby",
            especie="Perro",
            raza="Beagle",
            edad=5,
            dueno=cliente,
        )
        cita = Cita.objects.create(
            mascota=mascota,
            motivo="Limpieza",
            fecha=timezone.now() + timezone.timedelta(days=1),
        )
        user = User.objects.create_user(username="vet3", password="12345")
        user.groups.add(self.veterinaria_group)
        self.client.login(username="vet3", password="12345")

        response = self.client.post(
            reverse("citas"),
            {
                "cita_id": cita.id,
                "motivo": "Limpieza dental",
                "fecha": "2026-05-02T09:45",
            },
        )

        self.assertEqual(response.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.motivo, "Limpieza dental")
