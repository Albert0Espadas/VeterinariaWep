import json
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from .models import Cita, Cliente, Mascota, Pendiente, Venta


def ping(request):
    return JsonResponse({"status": "ok", "message": "VeterinariaWep activa"})


@csrf_exempt
def crear_cita(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Metodo no permitido"}, status=405)

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


def completar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.completado = True
    pendiente.save()
    return redirect("dashboard")


def eliminar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.delete()
    return redirect("dashboard")


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

    pendientes = Pendiente.objects.order_by("-fecha")
    citas = Cita.objects.select_related("mascota", "mascota__dueno").all()

    fecha_actual = now()
    hoy = fecha_actual.date()
    citas_hoy = citas.filter(fecha__date=hoy).order_by("fecha")
    futuras_citas = list(citas.filter(fecha__gte=fecha_actual).order_by("fecha")[:6])
    pendientes_completados = pendientes.filter(completado=True).count()
    pendientes_pendientes = pendientes.filter(completado=False).count()

    return render(
        request,
        "dashboard.html",
        {
            "pendientes": pendientes,
            "citas": citas,
            "citas_hoy": citas_hoy,
            "fecha_actual": fecha_actual,
            "total_mascotas": Mascota.objects.count(),
            "total_clientes": Cliente.objects.count(),
            "pendientes_completados": pendientes_completados,
            "pendientes_pendientes": pendientes_pendientes,
            "futuras_citas": futuras_citas,
        },
    )


def logout_view(request):
    logout(request)
    return redirect("login")

def recepcion(request):
    
    # GUARDAR CLIENTE
    if request.method == 'POST' and 'registrar_cliente' in request.POST:
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        email = request.POST.get('email')
        direccion = request.POST.get('direccion')

        Cliente.objects.create(
            nombre=nombre,
            telefono=telefono,
            email=email,
            direccion=direccion
        )

        return redirect('recepcion')

    # GUARDAR MASCOTA
    if request.method == 'POST' and 'registrar_mascota' in request.POST:
        nombre = request.POST.get('nombre_mascota')
        especie = request.POST.get('especie')
        raza = request.POST.get('raza')
        edad = request.POST.get('edad')
        cliente_id = request.POST.get('cliente')

        Mascota.objects.create(
            nombre=nombre,
            especie=especie,
            raza=raza,
            edad=edad,
            cliente_id=cliente_id
        )

        return redirect('recepcion')

    clientes = Cliente.objects.all()
    mascotas = Mascota.objects.all()

    return render(request, 'recepcion.html', {
        'clientes': clientes,
        'mascotas': mascotas
    })

def punto_venta(request):
    if request.method == 'POST':
        total = float(request.POST.get('total'))
        metodo = request.POST.get('metodo_pago')
        monto_pagado = float(request.POST.get('monto_pagado'))

        cambio = 0

        if metodo == 'efectivo':
            cambio = monto_pagado - total if monto_pagado >= total else 0

        venta = Venta.objects.create(
            total=total,
            metodo_pago=metodo,
            monto_pagado=monto_pagado,
            cambio=cambio
        )

        return render(request, 'pos.html', {
            'mensaje': 'Venta realizada con éxito',
            'cambio': cambio
        })

    return render(request, 'pos.html')