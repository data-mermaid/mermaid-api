from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Refresh materialized view used by the MERMAID API"

    def __init__(self):
        super(Command, self).__init__()
        self.refresh_sql = "REFRESH MATERIALIZED VIEW CONCURRENTLY {}"
        self.viewname = ""

    def handle(self, *args, **options):
        self.viewname = options.get("viewname")
        self.refresh_view()

    def add_arguments(self, parser):
        parser.add_argument("viewname", type=str)

    def refresh_view(self):
        sql = self.refresh_sql.format(self.viewname)
        with connection.cursor() as cursor:
            cursor.execute(sql)
