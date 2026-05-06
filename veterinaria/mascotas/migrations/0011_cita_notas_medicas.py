from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mascotas", "0010_create_role_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="cita",
            name="notas_medicas",
            field=models.TextField(blank=True, default=""),
        ),
    ]
