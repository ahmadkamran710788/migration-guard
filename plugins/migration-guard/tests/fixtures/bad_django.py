from django.db import migrations, models

def forwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [("shop", "0007_auto")]
    operations = [
        migrations.AddIndex(model_name="order", index=models.Index(fields=["status"], name="order_status_idx")),
        migrations.RenameField("order", "total", "total_cents"),
        migrations.RunPython(forwards),
    ]
