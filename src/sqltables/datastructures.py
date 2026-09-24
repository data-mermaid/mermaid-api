from typing import Any

from django.db.models import NOT_PROVIDED, ForeignObject  # type: ignore
from django.db.models.sql.datastructures import BaseTable  # type: ignore


class SQLTableArg:
    def __init__(self, sql: str = "", required: bool = True, default=NOT_PROVIDED):
        self.sql = sql
        self.required = required
        self.default = default


class SQLTable(BaseTable):
    sql_args: dict[str, "SQLTableParams"] = dict()

    def __init__(
        self,
        table_name: str,
        alias: str | None,
        sql_table_params: dict[str, Any],
        sql: str,
    ):
        super().__init__(table_name, alias)

        self.sql_table_params = sql_table_params
        self.sql = sql

    def as_sql(self, compiler, connection):
        # Resolve sql params from db_tables
        base_sql = self.sql % self.sql_table_params

        s = f"({base_sql}) {self.table_name}"
        return s, tuple()


class SQLTableParams:
    def __init__(self, level: int, join_field: ForeignObject, params: "dict[str, Any]"):
        self.level = level  # type: int
        self.join_field = join_field  # type: ForeignObject
        self.params = params  # type: dict[str, Any]
