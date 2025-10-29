from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('financials', '0002_initial'),  # последняя применённая миграция
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='personal_account',
            field=models.ForeignKey(
                to='financials.PersonalAccount',
                on_delete=models.CASCADE,
                null=True,
                blank=True,
            ),
        ),
    ]