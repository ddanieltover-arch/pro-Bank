# Generated manually for UK account sort_code

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_uk_destination_bank_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='sort_code',
            field=models.CharField(blank=True, max_length=8),
        ),
    ]
