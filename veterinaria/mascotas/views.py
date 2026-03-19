from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from .models import Pendiente
from django.contrib.auth import logout
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
            # GUARDAR EN BD
            Pendiente.objects.create(
                titulo=titulo,
                descripcion=descripcion
            )

        return redirect('dashboard')

    # OBTENER TODOS LOS PENDIENTES
    pendientes = Pendiente.objects.order_by('-fecha')
    total_pendientes = Pendiente.objects.count()
    pendientes_completados = Pendiente.objects.filter(completado=True).count()
    pendientes_pendientes = Pendiente.objects.filter(completado=False).count()
    return render(request, 'dashboard.html', {
        'pendientes': pendientes,
        'total_pendientes': total_pendientes,
        'pendientes_completados': pendientes_completados,
        'pendientes_pendientes': pendientes_pendientes
    })
def logout_view(request):
    logout(request)
    return redirect('login')