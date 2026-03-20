from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import json

from .models import Cita, Cliente, Mascota


class PingViewTests(TestCase):
    def test_ping_returns_ok_json(self):
        response = self.client.get(reverse("ping"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": "ok", "message": "VeterinariaWep activa"},
        )


class DashboardViewTests(TestCase):
    def test_dashboard_shows_real_metrics_and_future_appointments(self):
        User.objects.create_user(username="demo", password="12345")
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

        self.client.login(username="demo", password="12345")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pacientes Totales")
        self.assertContains(response, "Clientes")
        self.assertContains(response, "Pendientes Activos")
        self.assertContains(response, "Proximas Citas")
        self.assertContains(response, "Luna")
        self.assertContains(response, "Revision")
        self.assertContains(response, "Nueva cita")


class CrearCitaViewTests(TestCase):
    def test_crear_cita_returns_json_and_creates_related_records(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps(
                {
                    "mascota": "Milo",
                    "dueno": "Carla Gomez",
                    "motivo": "Desparasitacion",
                    "fecha": "2026-03-21T10:30:00",
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
