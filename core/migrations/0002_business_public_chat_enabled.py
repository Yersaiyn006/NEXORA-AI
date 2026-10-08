from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="business",
            name="public_chat_enabled",
            field=models.BooleanField(default=False, verbose_name="Публичный чат включён"),
        ),
    ]
