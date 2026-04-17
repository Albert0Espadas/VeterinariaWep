from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("mascotas", "0008_venta"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="cliente",
            table="anavet_clientes",
        ),
        migrations.AlterModelTable(
            name="mascota",
            table="anavet_mascotas",
        ),
        migrations.AlterModelTable(
            name="cita",
            table="anavet_citas",
        ),
        migrations.AlterModelTable(
            name="pendiente",
            table="anavet_pendientes",
        ),
        migrations.AlterModelTable(
            name="venta",
            table="anavet_ventas",
        ),
    ]
