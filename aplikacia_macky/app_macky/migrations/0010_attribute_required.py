# Generated by Django 4.2.1 on 2023-11-29 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_macky', '0009_record_description_recordcomment_aproved_by_admin_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='required',
            field=models.BooleanField(default=True),
        ),
    ]
