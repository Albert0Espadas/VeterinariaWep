from .roles import get_navigation_flags, get_primary_role


def anavet_shell(request):
    if not request.user.is_authenticated:
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

    return {
        "anavet_role": get_primary_role(request.user),
        "anavet_nav": get_navigation_flags(request.user),
    }
