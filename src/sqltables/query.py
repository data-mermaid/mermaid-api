import re
from typing import Any, Dict, List, Type

from django.db.models import NOT_PROVIDED, F, Manager, Model, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.db.models.sql import Query
from django.db.models.sql.datastructures import BaseTable
from django.db.models.sql.where import WhereNode

from .datastructures import SQLTable, SQLTableJoin, SQLTableParams


class SQLTableQuery(Query):
    def __init__(self, model, where=WhereNode):
        super().__init__(model, where)
        self.sql_table_params = []  # type: List[SQLTableParams]
        self.model_sql = model.sql

    def get_initial_alias(self):
        if self.alias_map:
            alias = self.base_table
            self.ref_alias(alias)
        else:

            if hasattr(self.model, "sql_args"):
                try:
                    params = list(
                        next(
                            filter(lambda x: x.level == 0, self.sql_table_params)
                        ).params.values()
                    )  # type: List[Any]
                except StopIteration:
                    # no parameters were passed from user
                    # so try to call the sql without parameters
                    # in case that they are optional
                    params = []

                alias = self.join(
                    SQLTable(self.get_meta().db_table, None, params, self.model_sql)
                )
            else:
                alias = self.join(BaseTable(self.get_meta().db_table, None))
        return alias

    def setup_joins(  # noqa: C901
        self,
        names,
        opts,
        alias,
        can_reuse=None,
        allow_many=True,
        reuse_with_filtered_relation=False,
    ):
        join_info = super().setup_joins(
            names, opts, alias, can_reuse, allow_many, reuse_with_filtered_relation
        )

        level = 0
        for alias in join_info.joins:
            join = self.alias_map[alias]
            if isinstance(join, SQLTable):
                # skip the `FROM func(...)`, it is handled in `get_initial_alias`
                continue
            if not hasattr(join.join_field.related_model, "sql_args"):
                # skip normal tables
                continue

            level += 1
            try:
                params = list(
                    next(
                        filter(
                            lambda x: x.level == level
                            and x.join_field == join.join_field,
                            self.sql_table_params,
                        )
                    ).params.values()
                )  # type: List[Any]
            except StopIteration:
                # no parameters were passed from user
                # so try to call the function without parameters
                # in case that they are optional
                params = []

            resolved_params = []
            for param in params:
                if isinstance(param, F):
                    resolved_param = param.resolve_expression(self)
                else:
                    resolved_param = param
                resolved_params.append(resolved_param)

            self.alias_map[alias] = SQLTableJoin(
                join.table_name,
                join.parent_alias,
                join.table_alias,
                join.join_type,
                join.join_field,
                join.nullable,
                self.model_sql,
                join.filtered_relation,
                resolved_params,
            )

        return join_info

    def sql_table(self, **sql_table_params: Dict[str, Any]):
        """
        Take user's passed params and store them in `self.sql_table_params`
        to be prepared for joining.
        """
        _sql_table_params = []
        for table_lookup, param_dict in self._sql_table_params_to_groups(
            sql_table_params
        ).items():
            if not table_lookup:
                level = 0
                join_field = None
                model = self.model
            else:
                level = len(table_lookup.split(LOOKUP_SEP))
                lookup_parts, field_parts, _ = self.solve_lookup_type(table_lookup)
                path, final_field, targets, rest = self.names_to_path(
                    field_parts, self.get_meta(), allow_many=False, fail_on_missing=True
                )
                join_field = path[-1].join_field
                model = final_field.related_model

            _sql_table_params.append(
                SQLTableParams(
                    level=level,
                    join_field=join_field,
                    params=self._reorder_sql_table_params(model, param_dict),
                )
            )

        # TODO: merge with existing?
        self.sql_table_params = _sql_table_params

    def _sql_table_params_to_groups(
        self, sql_table_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transfer user specified lookups into groups
        to have all parameters for each table function prepared for joining.

        {id: 1, parent__id: 2, parent__code=3, parent__parent__id=4, root__id=5}
            =>
        {
            '': {'id': 1},
            'parent': {'id': 2, 'code': 3},
            'parent__parent': {'id': 4},
            'root': {'id: 5}
        }
        """
        param_groups = {}
        for lookup, val in sql_table_params.items():
            parts = lookup.split(LOOKUP_SEP)
            prefix = LOOKUP_SEP.join(parts[:-1])
            field = parts[-1]
            if prefix not in param_groups:
                param_groups[prefix] = {}
            param_groups[prefix][field] = val
        return param_groups

    def _reorder_sql_table_params(  # noqa: C901
        self, model: Type[Model], sql_table_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make sure that parameters will be passed into function in correct order.
        Also check required and set defaults.
        """
        ordered_sql_params = dict()
        for key, arg in getattr(model, "sql_args").items():
            if key in sql_table_params:
                ordered_sql_params[key] = sql_table_params[key]
            elif arg.default != NOT_PROVIDED:
                ordered_sql_params[key] = arg.default
            elif arg.required:
                raise ValueError(f"Required function arg `{key}` not specified")

        remaining = set(sql_table_params.keys()) - set(ordered_sql_params.keys())
        if remaining:
            raise ValueError(f"SQL arg `{remaining.pop()}` not found")

        return ordered_sql_params


class SQLTableQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self.query = query or SQLTableQuery(self.model)

    def sql_table(self, **sql_table_params: Dict[str, Any]) -> "SQLTableQuerySet":
        self.query.sql_table(**sql_table_params)
        return self


class SQLTableManager(Manager):
    def get_queryset(self) -> SQLTableQuerySet:
        return SQLTableQuerySet(model=self.model, using=self._db, hints=self._hints)
