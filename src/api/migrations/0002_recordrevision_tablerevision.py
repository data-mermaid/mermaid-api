# Generated by Django 2.2.12 on 2021-04-13 17:04

from django.db import migrations, models
import django.db.models.deletion

from api.models import revisions

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordRevision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rev_id', models.UUIDField(db_index=True, editable=False, unique=True)),
                ('table_name', models.CharField(db_index=True, editable=False, max_length=50)),
                ('record_id', models.UUIDField(db_index=True, editable=False)),
                ('project_id', models.UUIDField(db_index=True, editable=False, null=True)),
                ('profile_id', models.UUIDField(db_index=True, editable=False, null=True)),
                ('updated_on', models.DateTimeField(editable=False)),
                ('deleted', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'db_table': 'record_revision',
                'unique_together': {('table_name', 'record_id')},
            },
        ),
        migrations.CreateModel(
            name='TableRevision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_revision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.RecordRevision')),
            ],
            options={
                'db_table': 'table_revision',
            },
        ),
        migrations.RunSQL(revisions.forward_sql, revisions.reverse_sql)
    ]
