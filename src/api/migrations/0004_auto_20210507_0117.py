# Generated by Django 2.2.12 on 2021-05-07 00:46

from django.db import migrations


forward_sql = """
    CREATE TABLE "mermaid_cache" (
        "cache_key" varchar(255) NOT NULL PRIMARY KEY,
        "value" text NOT NULL,
        "expires" timestamp with time zone NOT NULL
    );
    CREATE INDEX "mermaid_cache_expires" ON "mermaid_cache" ("expires");
"""

backward_sql = """
    DROP TABLE "mermaid_cache";
"""

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20210503_1830'),
    ]

    operations = [
        migrations.RunSQL(forward_sql, backward_sql)
    ]