# Generated by Django 2.2.12 on 2020-06-05 20:40

import django.contrib.gis.db.models.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_auto_20200601_1924'),
    ]

    operations = [
        migrations.CreateModel(
            name='BenthicLITObsView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_event_id', models.UUIDField()),
                ('sample_event_notes', models.TextField(blank=True)),
                ('sample_unit_id', models.UUIDField()),
                ('sample_time', models.TimeField()),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('transect_number', models.PositiveSmallIntegerField()),
                ('label', models.CharField(blank=True, max_length=50)),
                ('transect_len_surveyed', models.PositiveSmallIntegerField(verbose_name='transect length surveyed (m)')),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('reef_slope', models.CharField(max_length=50)),
                ('length', models.PositiveSmallIntegerField()),
                ('benthic_category', models.CharField(max_length=100)),
                ('benthic_attribute', models.CharField(max_length=100)),
                ('growth_form', models.CharField(max_length=100)),
                ('observation_notes', models.TextField(blank=True)),
                ('data_policy_benthiclit', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_benthiclit_obs',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BenthicLITSEView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_unit_count', models.PositiveSmallIntegerField()),
                ('depth_avg', models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth (m)')),
                ('percent_cover_by_benthic_category_avg', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('data_policy_benthiclit', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_benthiclit_se',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BenthicLITSUView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('transect_number', models.PositiveSmallIntegerField()),
                ('transect_len_surveyed', models.PositiveSmallIntegerField(verbose_name='transect length surveyed (m)')),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('reef_slope', models.CharField(max_length=50)),
                ('percent_cover_by_benthic_category', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('data_policy_benthiclit', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_benthiclit_su',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BleachingQCColoniesBleachedObsView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_event_id', models.UUIDField()),
                ('sample_event_notes', models.TextField(blank=True)),
                ('sample_unit_id', models.UUIDField()),
                ('sample_time', models.TimeField()),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('label', models.CharField(blank=True, max_length=50)),
                ('quadrat_size', models.DecimalField(decimal_places=2, max_digits=6)),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('benthic_attribute', models.CharField(max_length=100)),
                ('growth_form', models.CharField(max_length=100)),
                ('count_normal', models.PositiveSmallIntegerField(default=0, verbose_name='normal')),
                ('count_pale', models.PositiveSmallIntegerField(default=0, verbose_name='pale')),
                ('count_20', models.PositiveSmallIntegerField(default=0, verbose_name='0-20% bleached')),
                ('count_50', models.PositiveSmallIntegerField(default=0, verbose_name='20-50% bleached')),
                ('count_80', models.PositiveSmallIntegerField(default=0, verbose_name='50-80% bleached')),
                ('count_100', models.PositiveSmallIntegerField(default=0, verbose_name='80-100% bleached')),
                ('count_dead', models.PositiveSmallIntegerField(default=0, verbose_name='recently dead')),
                ('data_policy_bleachingqc', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_bleachingqc_colonies_bleached_obs',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BleachingQCQuadratBenthicPercentObsView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_event_id', models.UUIDField()),
                ('sample_event_notes', models.TextField(blank=True)),
                ('sample_unit_id', models.UUIDField()),
                ('sample_time', models.TimeField()),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('label', models.CharField(blank=True, max_length=50)),
                ('quadrat_size', models.DecimalField(decimal_places=2, max_digits=6)),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('quadrat_number', models.PositiveSmallIntegerField(verbose_name='quadrat number')),
                ('percent_hard', models.PositiveSmallIntegerField(default=0, verbose_name='hard coral, % cover')),
                ('percent_soft', models.PositiveSmallIntegerField(default=0, verbose_name='soft coral, % cover')),
                ('percent_algae', models.PositiveSmallIntegerField(default=0, verbose_name='macroalgae, % cover')),
                ('data_policy_bleachingqc', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_bleachingqc_quadrat_benthic_percent_obs',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BleachingQCSEView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_unit_count', models.PositiveSmallIntegerField()),
                ('depth_avg', models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth (m)')),
                ('quadrat_size_avg', models.DecimalField(decimal_places=2, max_digits=6)),
                ('count_total_avg', models.DecimalField(decimal_places=1, max_digits=5)),
                ('count_genera_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('percent_normal_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('percent_pale_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('percent_bleached_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('quadrat_count_avg', models.DecimalField(decimal_places=1, max_digits=3)),
                ('percent_hard_avg_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('percent_soft_avg_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('percent_algae_avg_avg', models.DecimalField(decimal_places=1, max_digits=4)),
                ('data_policy_bleachingqc', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_bleachingqc_se',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BleachingQCSUView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('label', models.CharField(blank=True, max_length=50)),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('quadrat_size', models.DecimalField(decimal_places=2, max_digits=6)),
                ('count_genera', models.PositiveSmallIntegerField(default=0)),
                ('count_total', models.PositiveSmallIntegerField(default=0)),
                ('percent_normal', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('percent_pale', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('percent_bleached', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('quadrat_count', models.PositiveSmallIntegerField(default=0)),
                ('percent_hard_avg', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('percent_soft_avg', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('percent_algae_avg', models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ('data_policy_bleachingqc', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_bleachingqc_su',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HabitatComplexityObsView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_event_id', models.UUIDField()),
                ('sample_event_notes', models.TextField(blank=True)),
                ('sample_unit_id', models.UUIDField()),
                ('sample_time', models.TimeField()),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('transect_number', models.PositiveSmallIntegerField()),
                ('label', models.CharField(blank=True, max_length=50)),
                ('transect_len_surveyed', models.PositiveSmallIntegerField(verbose_name='transect length surveyed (m)')),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('reef_slope', models.CharField(max_length=50)),
                ('interval', models.DecimalField(decimal_places=2, max_digits=7)),
                ('observation_notes', models.TextField(blank=True)),
                ('score', models.PositiveSmallIntegerField()),
                ('data_policy_habitatcomplexity', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_habitatcomplexity_obs',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HabitatComplexitySEView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('sample_unit_count', models.PositiveSmallIntegerField()),
                ('depth_avg', models.DecimalField(decimal_places=2, max_digits=4, verbose_name='depth (m)')),
                ('score_avg_avg', models.DecimalField(decimal_places=2, max_digits=3)),
                ('data_policy_habitatcomplexity', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_habitatcomplexity_se',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HabitatComplexitySUView',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('project_id', models.UUIDField()),
                ('project_name', models.CharField(max_length=255)),
                ('project_status', models.PositiveSmallIntegerField(choices=[(90, 'open'), (80, 'test'), (10, 'locked')], default=90)),
                ('project_notes', models.TextField(blank=True)),
                ('contact_link', models.CharField(max_length=255)),
                ('tags', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('site_id', models.UUIDField()),
                ('site_name', models.CharField(max_length=255)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('site_notes', models.TextField(blank=True)),
                ('country_id', models.UUIDField()),
                ('country_name', models.CharField(max_length=50)),
                ('reef_type', models.CharField(max_length=50)),
                ('reef_zone', models.CharField(max_length=50)),
                ('reef_exposure', models.CharField(max_length=50)),
                ('management_id', models.UUIDField()),
                ('management_name', models.CharField(max_length=255)),
                ('management_name_secondary', models.CharField(max_length=255)),
                ('management_est_year', models.PositiveSmallIntegerField()),
                ('management_size', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True, verbose_name='Size (ha)')),
                ('management_parties', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_compliance', models.CharField(max_length=100)),
                ('management_rules', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('management_notes', models.TextField(blank=True)),
                ('sample_date', models.DateField()),
                ('current_name', models.CharField(max_length=50)),
                ('tide_name', models.CharField(max_length=50)),
                ('visibility_name', models.CharField(max_length=50)),
                ('observers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('transect_number', models.PositiveSmallIntegerField()),
                ('transect_len_surveyed', models.PositiveSmallIntegerField(verbose_name='transect length surveyed (m)')),
                ('depth', models.DecimalField(decimal_places=1, max_digits=3, verbose_name='depth (m)')),
                ('reef_slope', models.CharField(max_length=50)),
                ('score_avg', models.DecimalField(decimal_places=2, max_digits=3)),
                ('data_policy_habitatcomplexity', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'vw_habitatcomplexity_su',
                'managed': False,
            },
        ),
    ]
