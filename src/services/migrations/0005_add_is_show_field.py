from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),  # или замени на последнюю свою миграцию
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_show',
            field=models.BooleanField(default=True, verbose_name='Показывать в счетчиках'),
        ),
    ]