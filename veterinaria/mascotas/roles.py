from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

ROLE_SECRETARIA = "Secretaria"
ROLE_VETERINARIA = "Veterinaria"
ROLE_ADMIN = "Administrador"

ROLE_PRIORITY = (
    ROLE_ADMIN,
    ROLE_VETERINARIA,
    ROLE_SECRETARIA,
)

STAFF_ROLES = (
    ROLE_SECRETARIA,
    ROLE_VETERINARIA,
    ROLE_ADMIN,
)


def get_user_role_names(user):
    if not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {ROLE_ADMIN}
    return set(user.groups.values_list("name", flat=True))


def get_primary_role(user):
    for role_name in ROLE_PRIORITY:
        if role_name in get_user_role_names(user):
            return role_name
    return "Sin rol"


def user_has_allowed_role(user, allowed_roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(get_user_role_names(user).intersection(set(allowed_roles)))


def roles_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if user_has_allowed_role(request.user, allowed_roles):
                return view_func(request, *args, **kwargs)
            messages.error(
                request,
                "Tu usuario no tiene permiso para entrar a esta seccion.",
            )
            return redirect("dashboard")

        return wrapped_view

    return decorator


def get_navigation_flags(user):
    return {
        "dashboard": user_has_allowed_role(user, STAFF_ROLES),
        "recepcion": user_has_allowed_role(user, (ROLE_SECRETARIA, ROLE_ADMIN)),
        "pos": user_has_allowed_role(user, (ROLE_SECRETARIA, ROLE_ADMIN)),
        "consultas": user_has_allowed_role(user, STAFF_ROLES),
        "citas": user_has_allowed_role(user, STAFF_ROLES),
    }
