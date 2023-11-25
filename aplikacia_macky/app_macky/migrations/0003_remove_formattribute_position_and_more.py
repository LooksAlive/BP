# Generated by Django 4.2.1 on 2023-11-07 16:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_macky', '0002_form_included_in_gallery_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='formattribute',
            name='position',
        ),
        migrations.AlterField(
            model_name='formattribute',
            name='record',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app_macky.record'),
        ),
        migrations.AlterField(
            model_name='recordcomment',
            name='record',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app_macky.record'),
        ),
    ]
