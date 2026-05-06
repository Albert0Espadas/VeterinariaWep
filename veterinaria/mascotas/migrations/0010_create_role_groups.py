from django.contrib.auth.models import Group, Permission, User
from django.db import migrations


ROLE_SECRETARIA = "Secretaria"
ROLE_VETERINARIA = "Veterinaria"
ROLE_ADMIN = "Administrador"


def create_role_groups(apps, schema_editor):
    secretaria_group, _ = Group.objects.get_or_create(name=ROLE_SECRETARIA)
    veterinaria_group, _ = Group.objects.get_or_create(name=ROLE_VETERINARIA)
    admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)

    mascotas_permissions = Permission.objects.filter(content_type__app_label="mascotas")

    secretaria_codes = {
        "add_cliente",
        "change_cliente",
        "delete_cliente",
        "view_cliente",
        "add_mascota",
        "change_mascota",
        "delete_mascota",
        "view_mascota",
        "add_cita",
        "change_cita",
        "view_cita",
        "add_pendiente",
        "change_pendiente",
        "delete_pendiente",
        "view_pendiente",
        "add_venta",
        "change_venta",
        "view_venta",
    }
    veterinaria_codes = {
        "view_cliente",
        "view_mascota",
        "view_cita",
        "add_cita",
        "change_cita",
        "view_pendiente",
        "add_pendiente",
        "change_pendiente",
    }

    secretaria_group.permissions.set(
        mascotas_permissions.filter(codename__in=secretaria_codes)
    )
    veterinaria_group.permissions.set(
        mascotas_permissions.filter(codename__in=veterinaria_codes)
    )
    admin_group.permissions.set(mascotas_permissions)

    for user in User.objects.filter(groups__isnull=True):
        user.groups.add(admin_group)


def reverse_role_groups(apps, schema_editor):
    Group.objects.filter(
        name__in=[ROLE_SECRETARIA, ROLE_VETERINARIA, ROLE_ADMIN]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("mascotas", "0009_rename_tables_anavet"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, reverse_role_groups),
    ]
