from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('financials', '0002_initial'),  # последняя миграция вашего приложения
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]