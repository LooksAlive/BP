# Generated by Django 4.2.1 on 2024-05-13 17:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_macky', '0016_rename_name_atribut_nazov_rename_type_atribut_typ_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formular_atribut_udaje',
            old_name='record',
            new_name='zaznam',
        ),
    ]