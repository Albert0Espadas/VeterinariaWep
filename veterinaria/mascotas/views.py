import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from .models import Cita, Cliente, Mascota, Pendiente, Venta


def ping(request):
    return JsonResponse({"status": "ok", "message": "VeterinariaWep activa"})


@login_required
@require_POST
def crear_cita(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON invalido"}, status=400)

    nombre_mascota = (data.get("mascota") or "").strip()
    nombre_dueno = (data.get("dueno") or "").strip() or "Cliente temporal"
    motivo = (data.get("motivo") or "").strip()
    fecha = data.get("fecha")

    if not nombre_mascota or not motivo or not fecha:
        return JsonResponse(
            {"status": "error", "message": "Mascota, motivo y fecha son obligatorios"},
            status=400,
        )

    try:
        fecha_cita = datetime.fromisoformat(fecha)
        if timezone.is_naive(fecha_cita):
            fecha_cita = timezone.make_aware(fecha_cita, timezone.get_current_timezone())
    except ValueError:
        return JsonResponse({"status": "error", "message": "Fecha invalida"}, status=400)

    cliente, _ = Cliente.objects.get_or_create(
        nombre=nombre_dueno,
        defaults={
            "telefono": "Pendiente",
            "email": f"{nombre_dueno.lower().replace(' ', '.')}@temporal.local",
        },
    )

    mascota, creada = Mascota.objects.get_or_create(
        nombre=nombre_mascota,
        defaults={
            "especie": "Desconocido",
            "raza": "Desconocido",
            "edad": 0,
            "dueno": cliente,
        },
    )

    if not creada and mascota.dueno_id != cliente.id:
        cliente = mascota.dueno

    cita = Cita.objects.create(
        mascota=mascota,
        motivo=motivo,
        fecha=fecha_cita,
    )

    return JsonResponse(
        {
            "status": "ok",
            "message": "Cita agendada correctamente",
            "cita": {
                "id": cita.id,
                "mascota": mascota.nombre,
                "dueno": cliente.nombre,
                "motivo": cita.motivo,
                "fecha": timezone.localtime(cita.fecha).strftime("%d/%m/%Y %H:%M"),
            },
        }
    )


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/dashboard")

        return render(request, "login.html", {"error": "Usuario o contrasena incorrectos"})

    return render(request, "login.html")


def registro_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        User.objects.create_user(username=username, password=password)
        return redirect("login")

    return render(request, "registro.html")


@login_required
@require_POST
def completar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.completado = True
    pendiente.save()
    return redirect("dashboard")


@login_required
@require_POST
def eliminar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.delete()
    return redirect("dashboard")


def _dashboard_context():
    pendientes = Pendiente.objects.order_by("-fecha")
    citas = Cita.objects.select_related("mascota", "mascota__dueno").order_by("fecha")
    fecha_actual = now()
    hoy = fecha_actual.date()

    return {
        "pendientes": pendientes,
        "citas": citas,
        "fecha_actual": fecha_actual,
        "citas_hoy": citas.filter(fecha__date=hoy),
        "futuras_citas": list(citas.filter(fecha__gte=fecha_actual)[:8]),
        "pendientes_completados": pendientes.filter(completado=True).count(),
        "pendientes_pendientes": pendientes.filter(completado=False).count(),
        "total_mascotas": Mascota.objects.count(),
        "total_clientes": Cliente.objects.count(),
    }


@login_required
def dashboard(request):
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        descripcion = request.POST.get("descripcion")

        if titulo:
            Pendiente.objects.create(
                titulo=titulo,
                descripcion=descripcion,
            )

        return redirect("dashboard")

    return render(request, "dashboard.html", _dashboard_context())


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def recepcion(request):
    mensaje = None

    if request.method == "POST" and "registrar_cliente" in request.POST:
        nombre = (request.POST.get("nombre") or "").strip()
        telefono = (request.POST.get("telefono") or "").strip()
        email = (request.POST.get("email") or "").strip() or "sin-correo@temporal.local"

        if nombre and telefono:
            Cliente.objects.create(
                nombre=nombre,
                telefono=telefono,
                email=email,
            )
            return redirect("recepcion")

        mensaje = "Completa al menos nombre y telefono del cliente."

    if request.method == "POST" and "registrar_mascota" in request.POST:
        nombre = (request.POST.get("nombre_mascota") or "").strip()
        especie = (request.POST.get("especie") or "").strip() or "Mascota"
        raza = (request.POST.get("raza") or "").strip() or "Sin especificar"
        edad = request.POST.get("edad") or 0
        cliente_id = request.POST.get("cliente")

        if nombre and cliente_id:
            Mascota.objects.create(
                nombre=nombre,
                especie=especie,
                raza=raza,
                edad=edad,
                dueno_id=cliente_id,
            )
            return redirect("recepcion")

        mensaje = "Selecciona un dueno y el nombre de la mascota."

    clientes = Cliente.objects.order_by("nombre")
    mascotas = Mascota.objects.select_related("dueno").order_by("nombre")

    return render(
        request,
        "recepcion.html",
        {
            "clientes": clientes,
            "mascotas": mascotas,
            "mensaje": mensaje,
            "total_clientes": clientes.count(),
            "total_mascotas": mascotas.count(),
            "clientes_recientes": clientes.order_by("-id")[:5],
            "mascotas_recientes": mascotas.order_by("-id")[:5],
        },
    )


@login_required
def punto_venta(request):
    mensaje = None
    error = None

    if request.method == "POST":
        try:
            total = Decimal(request.POST.get("total", "0"))
            metodo = request.POST.get("metodo_pago")
            monto_pagado = Decimal(request.POST.get("monto_pagado", "0"))
        except InvalidOperation:
            total = Decimal("0")
            metodo = request.POST.get("metodo_pago")
            monto_pagado = Decimal("0")
            error = "Ingresa montos validos para procesar la venta."
        else:
            cambio = Decimal("0.00")

            if total <= 0:
                error = "El total debe ser mayor a cero."
            elif metodo == "efectivo" and monto_pagado < total:
                error = "El monto recibido no puede ser menor al total."
            else:
                if metodo == "efectivo":
                    cambio = monto_pagado - total
                else:
                    monto_pagado = total

                Venta.objects.create(
                    total=total,
                    metodo_pago=metodo,
                    monto_pagado=monto_pagado,
                    cambio=cambio,
                )
                mensaje = "Venta registrada con exito."

    ventas = Venta.objects.order_by("-fecha")

    try:
        ventas_recientes = list(ventas[:6])
        ventas_hoy = list(ventas.filter(fecha__date=now().date()))
        total_hoy = sum((venta.total for venta in ventas_hoy), Decimal("0.00"))
        ventas_hoy_count = len(ventas_hoy)
        ultimo_metodo = ventas_recientes[0].metodo_pago if ventas_recientes else "sin ventas"
    except InvalidOperation:
        ventas_recientes = []
        total_hoy = Decimal("0.00")
        ventas_hoy_count = 0
        ultimo_metodo = "datos invalidos"
        if not error:
            error = "Hay ventas antiguas con formato invalido. La pagina sigue disponible, pero conviene limpiar esos registros."

    return render(
        request,
        "pos.html",
        {
            "mensaje": mensaje,
            "error": error,
            "ventas_recientes": ventas_recientes,
            "ventas_hoy_total": total_hoy,
            "ventas_hoy_count": ventas_hoy_count,
            "ultimo_metodo": ultimo_metodo,
        },
    )


@login_required
def consultas(request):
    citas = Cita.objects.select_related("mascota", "mascota__dueno").order_by("fecha")
    fecha_actual = now()
    hoy = fecha_actual.date()
    proximas_24h = citas.filter(fecha__gte=fecha_actual, fecha__lte=fecha_actual + timedelta(hours=24))
    citas_hoy = citas.filter(fecha__date=hoy)
    mascotas = Mascota.objects.select_related("dueno").order_by("nombre")

    return render(
        request,
        "consultas.html",
        {
            "fecha_actual": fecha_actual,
            "citas_hoy": citas_hoy,
            "proximas_24h": proximas_24h,
            "mascotas": mascotas[:8],
            "total_consultas_hoy": citas_hoy.count(),
            "total_proximas": proximas_24h.count(),
            "total_pacientes": Mascota.objects.count(),
        },
    )


@login_required
def citas(request):
    context = _dashboard_context()
    context.update(
        {
            "proximas_semanales": Cita.objects.select_related("mascota", "mascota__dueno")
            .filter(fecha__gte=now(), fecha__lte=now() + timedelta(days=7))
            .order_by("fecha"),
            "citas_pasadas": Cita.objects.select_related("mascota", "mascota__dueno")
            .filter(fecha__lt=now())
            .order_by("-fecha")[:6],
        }
    )
    return render(request, "citas.html", context)
