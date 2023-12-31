# Generated by Django 2.1.7 on 2023-08-13 08:13

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Anime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('update_time', models.DateTimeField(auto_now=True)),
                ('anime_name', models.TextField()),
                ('anime_id', models.TextField(unique=True)),
                ('episodes', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('coverImg', models.TextField(default='/public/anime/default.jpg')),
                ('state', models.TextField(default='Not start')),
                ('description', models.TextField()),
                ('category', models.TextField(default='teaching')),
                ('uploader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'Anime',
            },
        ),
        migrations.CreateModel(
            name='AnimeDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('father_road', models.IntegerField()),
                ('father_episode', models.IntegerField()),
                ('anime_format', models.TextField()),
                ('anime_resource', models.TextField()),
                ('father', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='anime.Anime')),
            ],
            options={
                'db_table': 'AnimeDetail',
            },
        ),
    ]
