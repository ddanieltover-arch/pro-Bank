# Generated manually for UK destination bank fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_transaction_destination_account_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='destination_account_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='transaction',
            name='destination_reference',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='transaction',
            name='destination_sort_code',
            field=models.CharField(blank=True, max_length=8),
        ),
    ]
