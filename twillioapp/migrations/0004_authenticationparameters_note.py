# Generated by Django 2.2.2 on 2019-06-29 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twillioapp', '0003_sentsms_have_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='authenticationparameters',
            name='note',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
