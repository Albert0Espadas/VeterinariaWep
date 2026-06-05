
import json
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cita, Cliente, Mascota, Pendiente, Venta
from .roles import (
    ROLE_ADMIN,
    ROLE_SECRETARIA,
    ROLE_VETERINARIA,
    get_primary_role,
    get_user_role_names,
    user_has_allowed_role,
)


# ══════════════════════════════════════════════════════════
# HELPERS — evitan repetir código en cada prueba
# ══════════════════════════════════════════════════════════

def crear_cliente(nombre="Juan Lopez", telefono="5550000001", email="juan@example.com"):
    return Cliente.objects.create(nombre=nombre, telefono=telefono, email=email)


def crear_mascota(nombre="Firulais", especie="Perro", raza="Labrador", edad=3, dueno=None):
    if dueno is None:
        dueno = crear_cliente()
    return Mascota.objects.create(nombre=nombre, especie=especie, raza=raza, edad=edad, dueno=dueno)


def crear_cita(mascota=None, motivo="Revisión general", horas=2):
    if mascota is None:
        mascota = crear_mascota()
    return Cita.objects.create(
        mascota=mascota,
        motivo=motivo,
        fecha=timezone.now() + timezone.timedelta(hours=horas),
    )


def crear_usuario_con_rol(username, rol, password="Pass1234"):
    grupo, _ = Group.objects.get_or_create(name=rol)
    user = User.objects.create_user(username=username, password=password)
    user.groups.add(grupo)
    return user


def login_como(client, rol, username=None, password="Pass1234"):
    """Crea usuario con el rol dado y hace login. Devuelve el usuario."""
    username = username or f"user_{rol.lower()}"
    user = crear_usuario_con_rol(username, rol, password)
    client.login(username=username, password=password)
    return user


# ══════════════════════════════════════════════════════════
# 1. PRUEBAS DE ENTRADA DE DATOS
#    · Nombres válidos · Correos · Contraseñas · Cantidades
# ══════════════════════════════════════════════════════════

class PruebasEntradaDatos(TestCase):

    def setUp(self):
        Group.objects.get_or_create(name=ROLE_SECRETARIA)
        login_como(self.client, ROLE_SECRETARIA, username="entrada_sec")

    # ── Nombres válidos ──────────────────────────────────
    def test_nombre_cliente_valido_se_guarda(self):
        """Un nombre de texto normal debe guardarse sin problema."""
        self.client.post(reverse("recepcion"), {
            "registrar_cliente": "1",
            "nombre": "María García López",
            "telefono": "5511223344",
            "email": "maria@example.com",
        })
        self.assertTrue(Cliente.objects.filter(nombre="María García López").exists())

    # ── Correo electrónico válido ────────────────────────
    def test_email_valido_se_acepta(self):
        """Un correo con formato correcto debe quedar registrado."""
        self.client.post(reverse("recepcion"), {
            "registrar_cliente": "1",
            "nombre": "Pedro",
            "telefono": "5511223344",
            "email": "pedro@correo.com",
        })
        self.assertEqual(Cliente.objects.get(nombre="Pedro").email, "pedro@correo.com")

    # ── Contraseña válida en registro ────────────────────
    def test_contrasena_valida_crea_usuario(self):
        """Contraseña con mayúscula, minúscula y número debe ser aceptada."""
        self.client.logout()
        response = self.client.post(reverse("registro"), {
            "username": "usuario_nuevo",
            "password": "Segura123",
            "password2": "Segura123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="usuario_nuevo").exists())

    # ── Cantidad numérica en POS ─────────────────────────
    def test_cantidad_numerica_en_venta_se_acepta(self):
        """Un monto válido en el POS debe crear la venta."""
        response = self.client.post(reverse("pos"), {
            "total": "350.00",
            "metodo_pago": "efectivo",
            "monto_pagado": "350.00",
        })
        self.assertEqual(Venta.objects.count(), 1)


# ══════════════════════════════════════════════════════════
# 2. PRUEBAS DE VALIDACIÓN
#    · Campos vacíos · Formatos incorrectos
#    · Datos fuera de rango · Letras en campos numéricos
# ══════════════════════════════════════════════════════════

class PruebasValidacion(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="val_sec")

    # ── Campos vacíos ────────────────────────────────────
    def test_crear_cita_sin_mascota_retorna_error(self):
        """Mascota vacía → error 400, sin cita creada."""
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "", "motivo": "Revisión", "fecha": "2026-09-01T10:00:00"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Cita.objects.count(), 0)

    def test_crear_cita_sin_motivo_retorna_error(self):
        """Motivo vacío → error 400."""
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "Max", "motivo": "", "fecha": "2026-09-01T10:00:00"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Formato incorrecto ───────────────────────────────
    def test_fecha_con_formato_incorrecto_retorna_error(self):
        """Una fecha con formato inválido no debe crear la cita."""
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "Rex", "motivo": "Vacuna", "fecha": "01-13-2026"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Letras en campo numérico (monto) ─────────────────
    def test_monto_con_letras_no_registra_venta(self):
        """Si el total contiene letras, la venta no se debe registrar."""
        response = self.client.post(reverse("pos"), {
            "total": "abc",
            "metodo_pago": "efectivo",
            "monto_pagado": "100.00",
        })
        self.assertEqual(Venta.objects.count(), 0)

    # ── Contraseña sin formato válido ────────────────────
    def test_contrasena_sin_mayuscula_es_rechazada(self):
        """Contraseña sin mayúscula no debe registrar usuario."""
        self.client.logout()
        self.client.post(reverse("registro"), {
            "username": "user_debil",
            "password": "sinmayuscula1",
            "password2": "sinmayuscula1",
        })
        self.assertFalse(User.objects.filter(username="user_debil").exists())

    def test_contrasena_sin_numero_es_rechazada(self):
        """Contraseña sin número no debe registrar usuario."""
        self.client.logout()
        self.client.post(reverse("registro"), {
            "username": "user_sinnumero",
            "password": "SinNumeroAqui",
            "password2": "SinNumeroAqui",
        })
        self.assertFalse(User.objects.filter(username="user_sinnumero").exists())


# ══════════════════════════════════════════════════════════
# 3. PRUEBAS DE LÍMITES
#    · Valores mínimos · Valores máximos
#    · Longitud máxima de texto · Cantidad máxima
# ══════════════════════════════════════════════════════════

class PruebasLimites(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="lim_sec")

    # ── Valor mínimo en venta ────────────────────────────
    def test_total_cero_no_registra_venta(self):
        """Un total de $0.00 no debe registrarse como venta válida."""
        self.client.post(reverse("pos"), {
            "total": "0.00",
            "metodo_pago": "efectivo",
            "monto_pagado": "0.00",
        })
        self.assertEqual(Venta.objects.count(), 0)

    # ── Valor mínimo: total negativo ─────────────────────
    def test_total_negativo_no_registra_venta(self):
        """Un monto negativo nunca debe procesarse."""
        self.client.post(reverse("pos"), {
            "total": "-50.00",
            "metodo_pago": "efectivo",
            "monto_pagado": "0.00",
        })
        self.assertEqual(Venta.objects.count(), 0)

    # ── Longitud máxima: nombre de mascota (100 chars) ───
    def test_nombre_mascota_en_limite_exacto_se_acepta(self):
        """100 caracteres es el límite del campo; debe guardarse."""
        nombre_largo = "A" * 100
        cliente = crear_cliente()
        self.client.post(reverse("recepcion"), {
            "registrar_mascota": "1",
            "nombre_mascota": nombre_largo,
            "especie": "Perro",
            "raza": "Mestizo",
            "edad": 2,
            "cliente": cliente.id,
        })
        self.assertTrue(Mascota.objects.filter(nombre=nombre_largo).exists())

    # ── Valor mínimo de edad ─────────────────────────────
    def test_mascota_con_edad_cero_se_acepta(self):
        """Edad 0 es válida (recién nacido)."""
        cliente = crear_cliente()
        self.client.post(reverse("recepcion"), {
            "registrar_mascota": "1",
            "nombre_mascota": "Bebé",
            "especie": "Gato",
            "raza": "Criollo",
            "edad": 0,
            "cliente": cliente.id,
        })
        self.assertTrue(Mascota.objects.filter(nombre="Bebé").exists())


# ══════════════════════════════════════════════════════════
# 4. PRUEBAS CRUD
#    · Insertar · Consultar · Actualizar · Eliminar
# ══════════════════════════════════════════════════════════

class PruebasCRUD(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="crud_sec")

    # ── CREATE: insertar cliente ─────────────────────────
    def test_insertar_cliente(self):
        self.client.post(reverse("recepcion"), {
            "registrar_cliente": "1",
            "nombre": "Nuevo Cliente",
            "telefono": "5512341234",
            "email": "nuevo@example.com",
        })
        self.assertEqual(Cliente.objects.filter(nombre="Nuevo Cliente").count(), 1)

    # ── READ: consultar cliente desde BD ─────────────────
    def test_consultar_cliente_existe(self):
        cliente = crear_cliente(nombre="Consulta Test")
        encontrado = Cliente.objects.get(nombre="Consulta Test")
        self.assertEqual(encontrado.id, cliente.id)
        self.assertEqual(encontrado.email, cliente.email)

    # ── UPDATE: actualizar datos de cliente ──────────────
    def test_actualizar_cliente(self):
        cliente = crear_cliente(nombre="Antes")
        self.client.post(reverse("editar_cliente", args=[cliente.id]), {
            "nombre": "Después",
            "telefono": "5599887766",
            "email": "despues@example.com",
        })
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre, "Después")
        self.assertEqual(cliente.telefono, "5599887766")

    # ── DELETE: eliminar cliente ─────────────────────────
    def test_eliminar_cliente(self):
        cliente = crear_cliente()
        self.client.post(reverse("eliminar_cliente", args=[cliente.id]))
        self.assertFalse(Cliente.objects.filter(id=cliente.id).exists())

    # ── CREATE: insertar mascota ─────────────────────────
    def test_insertar_mascota(self):
        cliente = crear_cliente()
        self.client.post(reverse("recepcion"), {
            "registrar_mascota": "1",
            "nombre_mascota": "Mascota Nueva",
            "especie": "Perro",
            "raza": "Poodle",
            "edad": 2,
            "cliente": cliente.id,
        })
        self.assertTrue(Mascota.objects.filter(nombre="Mascota Nueva").exists())

    # ── UPDATE: actualizar mascota ───────────────────────
    def test_actualizar_mascota(self):
        mascota = crear_mascota(nombre="Nombre Viejo")
        self.client.post(reverse("editar_mascota", args=[mascota.id]), {
            "nombre_mascota": "Nombre Nuevo",
            "especie": "Gato",
            "raza": "Siamés",
            "edad": 3,
            "cliente": mascota.dueno.id,
        })
        mascota.refresh_from_db()
        self.assertEqual(mascota.nombre, "Nombre Nuevo")

    # ── DELETE: eliminar mascota ─────────────────────────
    def test_eliminar_mascota(self):
        mascota = crear_mascota()
        self.client.post(reverse("eliminar_mascota", args=[mascota.id]))
        self.assertFalse(Mascota.objects.filter(id=mascota.id).exists())

    # ── CREATE: insertar cita ────────────────────────────
    def test_insertar_cita(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({
                "mascota": "Cita Mascota",
                "dueno": "Cita Dueño",
                "motivo": "Vacuna",
                "fecha": "2026-10-01T09:00:00",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cita.objects.count(), 1)

    # ── DELETE: eliminar cita ────────────────────────────
    def test_eliminar_cita_por_veterinaria(self):
        self.client.logout()
        login_como(self.client, ROLE_VETERINARIA, username="crud_vet")
        cita = crear_cita()
        self.client.get(reverse("eliminar_cita", args=[cita.id]))
        self.assertFalse(Cita.objects.filter(id=cita.id).exists())


# ══════════════════════════════════════════════════════════
# 5. PRUEBAS MATEMÁTICAS / CÁLCULOS
#    · Sumas · Cambio (equivalente a descuentos) · IVA
#    · Totales del día
# ══════════════════════════════════════════════════════════

class PruebasCalculos(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="calc_sec")

    def _venta(self, total, metodo, monto):
        self.client.post(reverse("pos"), {
            "total": str(total),
            "metodo_pago": metodo,
            "monto_pagado": str(monto),
        })

    # ── Cambio exacto ────────────────────────────────────
    def test_cambio_calculado_correctamente(self):
        """Pago de $300 con total $250 → cambio $50."""
        self._venta("250.00", "efectivo", "300.00")
        self.assertEqual(Venta.objects.first().cambio, Decimal("50.00"))

    # ── Sin cambio en tarjeta ────────────────────────────
    def test_tarjeta_no_genera_cambio(self):
        """En pago con tarjeta el cambio siempre es $0."""
        self._venta("400.00", "tarjeta", "400.00")
        self.assertEqual(Venta.objects.first().cambio, Decimal("0.00"))

    # ── Cambio de $0 cuando pago exacto ─────────────────
    def test_pago_exacto_en_efectivo_cambio_cero(self):
        self._venta("150.00", "efectivo", "150.00")
        self.assertEqual(Venta.objects.first().cambio, Decimal("0.00"))

    # ── Suma de ventas del día (total acumulado) ─────────
    def test_suma_ventas_del_dia(self):
        """Dos ventas de $100 y $200 deben sumar $300 en el total del día."""
        Venta.objects.create(total="100.00", metodo_pago="efectivo",
                             monto_pagado="100.00", cambio="0.00")
        Venta.objects.create(total="200.00", metodo_pago="tarjeta",
                             monto_pagado="200.00", cambio="0.00")
        ventas_hoy = Venta.objects.filter(fecha__date=timezone.now().date())
        total = sum(v.total for v in ventas_hoy)
        self.assertEqual(total, Decimal("300.00"))

    # ── Cambio con centavos ──────────────────────────────
    def test_cambio_con_decimales_es_preciso(self):
        """El sistema debe manejar centavos sin error de redondeo."""
        self._venta("99.99", "efectivo", "100.00")
        self.assertEqual(Venta.objects.first().cambio, Decimal("0.01"))


# ══════════════════════════════════════════════════════════
# 6. PRUEBAS DE LÓGICA DE NEGOCIO
#    · No vender por debajo del total · Sin duplicados
#    · Validar datos clínicos
# ══════════════════════════════════════════════════════════

class PruebasLogicaNegocio(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="neg_sec")

    # ── No procesar venta si monto es insuficiente ───────
    def test_no_vender_si_monto_insuficiente(self):
        """Equivalente a 'no vender sin stock': si el pago no cubre el total, se rechaza."""
        self.client.post(reverse("pos"), {
            "total": "500.00",
            "metodo_pago": "efectivo",
            "monto_pagado": "100.00",
        })
        self.assertEqual(Venta.objects.count(), 0)

    # ── No crear cliente duplicado ───────────────────────
    def test_crear_cita_reutiliza_cliente_existente(self):
        """Si el dueño ya existe, no debe crear un duplicado."""
        crear_cliente(nombre="Dueño Existente")
        self.client.post(
            reverse("crear_cita"),
            data=json.dumps({
                "mascota": "Rex",
                "dueno": "Dueño Existente",
                "motivo": "Vacuna",
                "fecha": "2026-10-01T09:00:00",
            }),
            content_type="application/json",
        )
        self.assertEqual(Cliente.objects.filter(nombre="Dueño Existente").count(), 1)

    # ── No crear mascota duplicada al reagendar ──────────
    def test_crear_cita_reutiliza_mascota_existente(self):
        """Si la mascota ya existe, no debe duplicarse al crear nueva cita."""
        mascota = crear_mascota(nombre="Luna")
        self.client.post(
            reverse("crear_cita"),
            data=json.dumps({
                "mascota": "Luna",
                "dueno": "Alguien",
                "motivo": "Revisión",
                "fecha": "2026-10-01T09:00:00",
            }),
            content_type="application/json",
        )
        self.assertEqual(Mascota.objects.filter(nombre="Luna").count(), 1)

    # ── Pendiente inicia sin completar ───────────────────
    def test_pendiente_nuevo_no_esta_completado(self):
        p = Pendiente.objects.create(titulo="Tarea", descripcion="desc")
        self.assertFalse(p.completado)

    # ── Completar pendiente cambia su estado ─────────────
    def test_completar_pendiente_marca_como_hecho(self):
        p = Pendiente.objects.create(titulo="Llamar", descripcion="Confirmar")
        self.client.post(reverse("completar", args=[p.id]))
        p.refresh_from_db()
        self.assertTrue(p.completado)

    # ── Notas médicas inician vacías ─────────────────────
    def test_cita_nueva_sin_notas_medicas(self):
        """Por regla de negocio, las notas médicas solo las agrega el veterinario."""
        cita = crear_cita()
        self.assertEqual(cita.notas_medicas, "")


# ══════════════════════════════════════════════════════════
# 7. PRUEBAS DE AUTENTICACIÓN
#    · Login correcto · Contraseña incorrecta
#    · Usuario inexistente · Contraseñas que no coinciden
# ══════════════════════════════════════════════════════════

class PruebasAutenticacion(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="auth_user", password="Pass1234")

    # ── Login correcto ───────────────────────────────────
    def test_login_correcto_redirige_a_dashboard(self):
        response = self.client.post(reverse("login"), {
            "username": "auth_user",
            "password": "Pass1234",
        })
        self.assertRedirects(response, "/dashboard")

    # ── Contraseña incorrecta ────────────────────────────
    def test_login_con_contrasena_incorrecta_muestra_error(self):
        response = self.client.post(reverse("login"), {
            "username": "auth_user",
            "password": "MalPass99",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrectos")

    # ── Usuario inexistente ──────────────────────────────
    def test_login_con_usuario_inexistente_muestra_error(self):
        response = self.client.post(reverse("login"), {
            "username": "no_existe",
            "password": "Pass1234",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrectos")

    # ── Contraseñas que no coinciden en registro ─────────
    def test_registro_contrasenas_no_coinciden_no_crea_usuario(self):
        Group.objects.get_or_create(name=ROLE_SECRETARIA)
        self.client.post(reverse("registro"), {
            "username": "usuario_fallo",
            "password": "Pass1234",
            "password2": "OtraPass9",
        })
        self.assertFalse(User.objects.filter(username="usuario_fallo").exists())

    # ── Logout cierra la sesión ──────────────────────────
    def test_logout_impide_acceso_al_dashboard(self):
        self.client.login(username="auth_user", password="Pass1234")
        self.client.get(reverse("logout"))
        response = self.client.get(reverse("dashboard"))
        # Sin sesión debe redirigir al login
        self.assertNotEqual(response.status_code, 200)

    # ── Vista protegida sin login redirige ───────────────
    def test_dashboard_sin_login_redirige_a_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)


# ══════════════════════════════════════════════════════════
# 8. PRUEBAS DE AUTORIZACIÓN — PERMISOS POR ROLES
#    · Secretaria · Veterinaria · Administrador
# ══════════════════════════════════════════════════════════

class PruebasAutorizacion(TestCase):

    # ── Secretaria NO accede a eliminar cita ────────────
    def test_secretaria_no_puede_eliminar_cita(self):
        login_como(self.client, ROLE_SECRETARIA, username="auth_sec")
        cita = crear_cita()
        self.client.get(reverse("eliminar_cita", args=[cita.id]))
        self.assertTrue(Cita.objects.filter(id=cita.id).exists())

    # ── Veterinaria NO accede a recepción ────────────────
    def test_veterinaria_no_puede_entrar_a_recepcion(self):
        login_como(self.client, ROLE_VETERINARIA, username="auth_vet")
        response = self.client.get(reverse("recepcion"))
        self.assertRedirects(response, reverse("dashboard"))

    # ── Veterinaria NO accede al POS ────────────────────
    def test_veterinaria_no_puede_entrar_a_pos(self):
        login_como(self.client, ROLE_VETERINARIA, username="auth_vet2")
        response = self.client.get(reverse("pos"))
        self.assertRedirects(response, reverse("dashboard"))

    # ── Secretaria puede ver consultas (solo lectura) ────
    def test_secretaria_ve_consultas_en_modo_lectura(self):
        login_como(self.client, ROLE_SECRETARIA, username="auth_sec2")
        response = self.client.get(reverse("consultas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modo Lectura")

    # ── Secretaria NO puede editar consulta ─────────────
    def test_secretaria_no_puede_editar_consulta(self):
        login_como(self.client, ROLE_SECRETARIA, username="auth_sec3")
        cita = crear_cita(motivo="Original")
        self.client.post(reverse("consultas"), {
            "cita_id": cita.id,
            "motivo": "Bloqueado",
            "fecha": "2026-09-01T10:00",
        })
        cita.refresh_from_db()
        self.assertEqual(cita.motivo, "Original")

    # ── Veterinaria SÍ puede editar consulta ────────────
    def test_veterinaria_puede_editar_consulta(self):
        login_como(self.client, ROLE_VETERINARIA, username="auth_vet3")
        cita = crear_cita(motivo="Sin editar")
        self.client.post(reverse("consultas"), {
            "cita_id": cita.id,
            "motivo": "Editado por vet",
            "fecha": "2026-09-01T10:00",
            "notas_medicas": "Paciente sano.",
        })
        cita.refresh_from_db()
        self.assertEqual(cita.motivo, "Editado por vet")

    # ── Administrador accede a todo ──────────────────────
    def test_admin_puede_entrar_a_recepcion(self):
        login_como(self.client, ROLE_ADMIN, username="auth_admin")
        response = self.client.get(reverse("recepcion"))
        self.assertEqual(response.status_code, 200)

    # ── helper user_has_allowed_role ────────────────────
    def test_superusuario_tiene_acceso_total(self):
        sup = User.objects.create_superuser("sup_test", password="Pass1234")
        self.assertTrue(user_has_allowed_role(sup, [ROLE_SECRETARIA]))

    def test_usuario_sin_rol_no_tiene_acceso(self):
        user = User.objects.create_user("sin_rol", password="Pass1234")
        self.assertFalse(user_has_allowed_role(user, [ROLE_ADMIN]))


# ══════════════════════════════════════════════════════════
# 9. PRUEBAS DE MANEJO DE ERRORES
#    · Datos nulos · Valores inválidos · Total incorrecto
# ══════════════════════════════════════════════════════════

class PruebasManejoErrores(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="err_sec")

    # ── Datos nulos en venta ─────────────────────────────
    def test_total_nulo_no_registra_venta(self):
        """Sin total la venta no debe procesarse."""
        response = self.client.post(reverse("pos"), {
            "total": "",
            "metodo_pago": "efectivo",
            "monto_pagado": "100.00",
        })
        self.assertEqual(Venta.objects.count(), 0)

    # ── Fecha inválida en cita ───────────────────────────
    def test_fecha_invalida_en_cita_retorna_400(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "Max", "motivo": "Test", "fecha": "esto-no-es-fecha"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Monto insuficiente en POS ────────────────────────
    def test_monto_menor_al_total_muestra_error_en_pos(self):
        response = self.client.post(reverse("pos"), {
            "total": "300.00",
            "metodo_pago": "efectivo",
            "monto_pagado": "50.00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "menor")
        self.assertEqual(Venta.objects.count(), 0)

    # ── Pendiente inexistente devuelve 404 ───────────────
    def test_completar_pendiente_inexistente_retorna_404(self):
        response = self.client.post(reverse("completar", args=[9999]))
        self.assertEqual(response.status_code, 404)

    # ── Cita inexistente en consultas devuelve 404 ───────
    def test_editar_cita_inexistente_retorna_404(self):
        self.client.logout()
        login_como(self.client, ROLE_VETERINARIA, username="err_vet")
        response = self.client.post(reverse("consultas"), {
            "cita_id": 9999,
            "motivo": "Nada",
            "fecha": "2026-09-01T10:00",
        })
        self.assertEqual(response.status_code, 404)


# ══════════════════════════════════════════════════════════
# 10. PRUEBAS DE EXCEPCIONES
#     · JSON inválido · Body vacío · Método HTTP incorrecto
# ══════════════════════════════════════════════════════════

class PruebasExcepciones(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="exc_sec")

    # ── JSON inválido en crear_cita ──────────────────────
    def test_json_invalido_en_crear_cita_retorna_400(self):
        response = self.client.post(
            reverse("crear_cita"),
            data="{ esto no : es json }",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")

    # ── Body completamente vacío ─────────────────────────
    def test_body_vacio_en_crear_cita_retorna_400(self):
        response = self.client.post(
            reverse("crear_cita"),
            data="",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Método GET en endpoint que requiere POST ─────────
    def test_get_en_completar_pendiente_retorna_405(self):
        p = Pendiente.objects.create(titulo="Test", descripcion="desc")
        response = self.client.get(reverse("completar", args=[p.id]))
        self.assertEqual(response.status_code, 405)

    # ── Mensaje de error en respuesta JSON ──────────────
    def test_respuesta_error_contiene_mensaje(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "", "motivo": "", "fecha": ""}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertIn("message", data)
        self.assertNotEqual(data["message"], "")


# ══════════════════════════════════════════════════════════
# 11. PRUEBAS DE BASE DE DATOS
#     · Inserción · Consulta · Actualización · Eliminación
#     · Integridad referencial (cascada)
# ══════════════════════════════════════════════════════════

class PruebasBaseDatos(TestCase):

    # ── Inserción correcta ───────────────────────────────
    def test_insercion_cliente_persiste_en_bd(self):
        cliente = Cliente.objects.create(
            nombre="BD Test", telefono="5500000000", email="bd@test.com"
        )
        self.assertIsNotNone(cliente.id)
        self.assertTrue(Cliente.objects.filter(id=cliente.id).exists())

    # ── Consulta correcta ────────────────────────────────
    def test_consulta_recupera_datos_correctos(self):
        crear_cliente(nombre="Consulta BD", email="consulta@bd.com")
        cliente = Cliente.objects.get(nombre="Consulta BD")
        self.assertEqual(cliente.email, "consulta@bd.com")

    # ── Actualización exitosa ────────────────────────────
    def test_actualizacion_guarda_nuevo_valor(self):
        cliente = crear_cliente(nombre="Antes")
        cliente.nombre = "Después"
        cliente.save()
        self.assertEqual(Cliente.objects.get(id=cliente.id).nombre, "Después")

    # ── Eliminación correcta ─────────────────────────────
    def test_eliminacion_borra_registro(self):
        cliente = crear_cliente()
        cliente_id = cliente.id
        cliente.delete()
        self.assertFalse(Cliente.objects.filter(id=cliente_id).exists())

    # ── Integridad referencial: cascada cliente→mascota ──
    def test_borrar_cliente_borra_sus_mascotas(self):
        cliente = crear_cliente()
        crear_mascota(dueno=cliente)
        cliente.delete()
        self.assertEqual(Mascota.objects.count(), 0)

    # ── Integridad referencial: cascada mascota→cita ─────
    def test_borrar_mascota_borra_sus_citas(self):
        mascota = crear_mascota()
        crear_cita(mascota=mascota)
        mascota.delete()
        self.assertEqual(Cita.objects.count(), 0)

    # ── Tablas personalizadas ────────────────────────────
    def test_tabla_clientes_tiene_nombre_correcto(self):
        self.assertEqual(Cliente._meta.db_table, "anavet_clientes")

    def test_tabla_mascotas_tiene_nombre_correcto(self):
        self.assertEqual(Mascota._meta.db_table, "anavet_mascotas")

    def test_tabla_citas_tiene_nombre_correcto(self):
        self.assertEqual(Cita._meta.db_table, "anavet_citas")


# ══════════════════════════════════════════════════════════
# 12. PRUEBAS DE APIs / SERVICIOS
#     · Respuesta correcta · JSON válido · Códigos HTTP
# ══════════════════════════════════════════════════════════

class PruebasAPI(TestCase):

    def setUp(self):
        login_como(self.client, ROLE_SECRETARIA, username="api_sec")

    # ── Ping responde con JSON correcto ──────────────────
    def test_ping_devuelve_status_ok(self):
        response = self.client.get(reverse("ping"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "status": "ok",
            "message": "VeterinariaWep activa",
        })

    # ── Crear cita devuelve JSON válido ──────────────────
    def test_crear_cita_devuelve_json_con_datos(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({
                "mascota": "API Mascota",
                "dueno": "API Dueño",
                "motivo": "Control",
                "fecha": "2026-11-01T10:00:00",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ok")
        self.assertIn("cita", data)
        self.assertEqual(data["cita"]["mascota"], "API Mascota")

    # ── Error retorna JSON con campo message ─────────────
    def test_error_devuelve_json_con_message(self):
        response = self.client.post(
            reverse("crear_cita"),
            data=json.dumps({"mascota": "", "motivo": "", "fecha": ""}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertIn("message", data)

    # ── Código 400 en datos inválidos ────────────────────
    def test_datos_invalidos_retornan_codigo_400(self):
        response = self.client.post(
            reverse("crear_cita"),
            data="no es json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # ── Ping no requiere autenticación ───────────────────
    def test_ping_funciona_sin_login(self):
        self.client.logout()
        response = self.client.get(reverse("ping"))
        self.assertEqual(response.status_code, 200)


# ══════════════════════════════════════════════════════════
# 13. PRUEBAS DE INTERFACES INTERNAS (MODELOS)
#     · Métodos __str__ · Relaciones · Valores por defecto
# ══════════════════════════════════════════════════════════

class PruebasInterfacesInternas(TestCase):

    # ── __str__ de cada modelo ───────────────────────────
    def test_str_cliente_devuelve_nombre(self):
        c = crear_cliente(nombre="Str Test")
        self.assertEqual(str(c), "Str Test")

    def test_str_mascota_devuelve_nombre(self):
        m = crear_mascota(nombre="Bobby")
        self.assertEqual(str(m), "Bobby")

    def test_str_pendiente_devuelve_titulo(self):
        p = Pendiente.objects.create(titulo="Mi tarea", descripcion="desc")
        self.assertEqual(str(p), "Mi tarea")

    def test_str_venta_incluye_total(self):
        v = Venta.objects.create(
            total="750.00", metodo_pago="efectivo", monto_pagado="750.00"
        )
        self.assertIn("750", str(v))

    def test_str_cita_incluye_nombre_mascota(self):
        m = crear_mascota(nombre="Coco")
        c = crear_cita(mascota=m)
        self.assertIn("Coco", str(c))

    # ── Relación mascota → dueño ─────────────────────────
    def test_mascota_tiene_referencia_a_su_dueno(self):
        cliente = crear_cliente(nombre="Dueño Real")
        mascota = crear_mascota(dueno=cliente)
        self.assertEqual(mascota.dueno.nombre, "Dueño Real")

    # ── Relación cita → mascota → dueño (encadenada) ─────
    def test_cita_llega_al_dueno_por_cadena(self):
        cliente = crear_cliente(nombre="Cadena Dueño")
        mascota = crear_mascota(dueno=cliente)
        cita = crear_cita(mascota=mascota)
        self.assertEqual(cita.mascota.dueno.nombre, "Cadena Dueño")

    # ── get_primary_role respeta prioridad ───────────────
    def test_get_primary_role_admin_sobre_secretaria(self):
        user = crear_usuario_con_rol("prio_user", ROLE_SECRETARIA)
        admin_grupo, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        user.groups.add(admin_grupo)
        self.assertEqual(get_primary_role(user), ROLE_ADMIN)

    # ── Valor por defecto: completado=False ──────────────
    def test_pendiente_completado_inicia_en_false(self):
        p = Pendiente.objects.create(titulo="X", descripcion="Y")
        self.assertFalse(p.completado)

    # ── Valor por defecto: notas_medicas vacío ───────────
    def test_cita_notas_medicas_inician_vacias(self):
        cita = crear_cita()
        self.assertEqual(cita.notas_medicas, "")

    # ── Conversión de Decimal en cambio ──────────────────
    def test_cambio_guardado_como_decimal(self):
        v = Venta.objects.create(
            total="200.00", metodo_pago="efectivo",
            monto_pagado="250.00", cambio="50.00"
        )
        self.assertIsInstance(v.cambio, Decimal)