# Generated by Django 4.2.1 on 2023-11-29 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_macky', '0010_attribute_required'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attribute',
            name='required',
        ),
        migrations.AddField(
            model_name='formattribute',
            name='required',
            field=models.BooleanField(default=True),
        ),
    ]
