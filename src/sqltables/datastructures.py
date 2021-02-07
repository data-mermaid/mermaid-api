import re
from typing import Any, Dict, List, Optional

from django.db.models import NOT_PROVIDED, ForeignObject
from django.db.models.sql.datastructures import BaseTable, Join


class SQLTableArg:
    def __init__(self, required: bool = True, default=NOT_PROVIDED):
        self.required = required  # type: bool
        self.default = default


class SQLTable(BaseTable):
    sql_args = dict()

    def __init__(
        self,
        table_name: str,
        alias: Optional[str],
        sql_table_params: List[Any],
        sql: str,
    ):
        super().__init__(table_name, alias)

        self.sql_table_params = sql_table_params  # type: List[Any]
        self.sql = sql  # type: List[Any]

    def as_sql(self, compiler, connection):
        # Resolve sql params from db_table
        base_sql = self.sql % tuple(self.sql_table_params)

        s = f"({base_sql}) {self.table_name}"
        return s, tuple()


class SQLTableJoin(Join):
    def __init__(
        self,
        table_name,
        parent_alias,
        table_alias,
        join_type,
        join_field,
        nullable,
        table_sql: str,
        filtered_relation=None,
        sql_table_params: List[Any] = None,
    ):
        super().__init__(
            table_name,
            parent_alias,
            table_alias,
            join_type,
            join_field,
            nullable,
            filtered_relation,
        )
        self.sql_table_params = sql_table_params  # type: List[Any]
        self.table_sql = table_sql

    def as_sql(self, compiler, connection):
        sql, params = super().as_sql(compiler, connection)
        if self.sql_table_params is None:
            return sql, params  # normal table join

        # extract `on_clause_sql` from ancestor's complex compiled query logic
        # to be able pass function instead of normal table into sql easily
        result = re.match(
            ".+?join.+?on(?P<on_clause_sql>.+)", sql, re.IGNORECASE | re.DOTALL
        )
        on_clause_sql = result.group("on_clause_sql")

        sql_table_placeholders = []
        sql_table_params = []
        for param in self.sql_table_params:
            if hasattr(param, "as_sql"):
                param_sql, param_params = param.as_sql(compiler, connection)
            else:
                param_sql = "%s"
                param_params = [param]
            sql_table_placeholders.append(param_sql)
            sql_table_params += param_params

        sql = f"""
            {self.join_type} ({self.table_sql})
            {self.table_alias} ON ({on_clause_sql})
        """
        return sql, sql_table_params + params


class SQLTableParams:
    def __init__(self, level: int, join_field: ForeignObject, params: "Dict[str, Any]"):
        self.level = level  # type: int
        self.join_field = join_field  # type: ForeignObject
        self.params = params  # type: dict[str, Any]
