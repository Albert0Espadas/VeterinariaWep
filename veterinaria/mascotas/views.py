from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from .models import Pendiente

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

def dashboard(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')

        # GUARDAR EN BD
        Pendiente.objects.create(
            titulo=titulo,
            descripcion=descripcion
        )

        return redirect('dashboard')

    # OBTENER TODOS LOS PENDIENTES
    pendientes = Pendiente.objects.all()

    return render(request, 'dashboard.html', {
        'pendientes': pendientes
    })