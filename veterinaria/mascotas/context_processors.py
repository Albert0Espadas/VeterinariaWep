from .roles import get_navigation_flags, get_primary_role


def anavet_shell(request):
    # Este context processor es el puente silencioso entre backend y frontend:
    # toma el usuario actual, calcula rol y permisos visibles, y los inyecta
    # en todos los templates para que el menu lateral se adapte automaticamente.
    if not request.user.is_authenticated:
        # Cuando no hay sesion iniciada, el layout recibe un estado neutral
        # para no mostrar accesos internos del sistema.
        return {
            "anavet_role": "Invitado",
            "anavet_nav": {
                "dashboard": False,
                "recepcion": False,
                "pos": False,
                "consultas": False,
                "citas": False,
            },
        }

    # Si el usuario ya inicio sesion, se inyecta su rol principal y los
    # modulos visibles para que el template base los pinte automaticamente.
    return {
        "anavet_role": get_primary_role(request.user),
        "anavet_nav": get_navigation_flags(request.user),
    }
