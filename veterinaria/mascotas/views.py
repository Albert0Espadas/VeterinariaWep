from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from .models import Pendiente
from django.contrib.auth import logout
from .models import Pendiente, Cita
from django.http import JsonResponse
import json
from .models import Cita
from datetime import date
from .models import Cita, Mascota
from django.utils.timezone import now
from .models import Cita, Mascota
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def crear_cita(request):

    if request.method == "POST":

        data = json.loads(request.body)

        nombre_mascota = data.get("mascota")
        motivo = data.get("motivo")
        fecha = data.get("fecha")

        mascota, created = Mascota.objects.get_or_create(
            nombre=nombre_mascota,
            defaults={
                "especie": "Desconocido",
                "raza": "Desconocido",
                "edad": 0,
                "dueno_id": 1
            }
        )

        Cita.objects.create(
            mascota=mascota,
            motivo=motivo,
            fecha=fecha
        )

        return JsonResponse({"status": "ok"})
def login_view(request):

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/dashboard')
        else:
            return render(request, 'login.html', {'error': 'Usuario o contraseña incorrectos'})

    return render(request, 'login.html')


def registro_view(request):

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        User.objects.create_user(username=username, password=password)

        return redirect('login')

    return render(request, 'registro.html')

def completar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.completado = True
    pendiente.save()
    return redirect('dashboard')


def eliminar_pendiente(request, id):
    pendiente = get_object_or_404(Pendiente, id=id)
    pendiente.delete()
    return redirect('dashboard')

@login_required
def dashboard(request):

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')

        if titulo:
            Pendiente.objects.create(
                titulo=titulo,
                descripcion=descripcion
            )

        return redirect('dashboard')

    pendientes = Pendiente.objects.order_by('-fecha')
    citas = Cita.objects.all()

    hoy = now().date()
    citas_hoy = Cita.objects.filter(fecha__date=hoy)

    return render(request, 'dashboard.html', {
        'pendientes': pendientes,
        'citas': citas,
        'citas_hoy': citas_hoy
    })
def logout_view(request):
    logout(request)
    return redirect('login')