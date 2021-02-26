# Generated by Django 2.2.12 on 2021-01-30 16:17

import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_project_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='management',
            name='est_year',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(2021)], verbose_name='year established'),
        ),
        migrations.AlterField(
            model_name='mpa',
            name='est_year',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(2021)], verbose_name='year established'),
        ),
        migrations.CreateModel(
            name='Covariate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('name', models.CharField(choices=[('aca_benthic', 'aca_benthic'), ('aca_geomorphic', 'aca_geomorphic')], max_length=100)),
                ('display', models.CharField(max_length=100)),
                ('datestamp', models.DateField()),
                ('requested_datestamp', models.DateField()),
                ('value', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='covariate_created_by', to='api.Profile')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='covariates', to='api.Site')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='covariate_updated_by', to='api.Profile')),
            ],
            options={
                'unique_together': {('site', 'name')},
            },
        ),
    ]