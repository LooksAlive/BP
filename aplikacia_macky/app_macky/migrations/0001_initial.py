# Generated by Django 4.2.1 on 2023-11-04 18:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('thumb_up', models.PositiveIntegerField(default=0)),
                ('thumb_down', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='RecordComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app_macky.record')),
            ],
        ),
        migrations.CreateModel(
            name='FormAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField()),
                ('value', models.CharField(blank=True, max_length=255, null=True)),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app_macky.attribute')),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app_macky.form')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app_macky.record')),
            ],
        ),
    ]