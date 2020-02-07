import pytz
from django.db.models import ProtectedError, Q
from django.http.response import HttpResponseBadRequest
from django.template.defaultfilters import pluralize
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action

from ..models import ArchivedRecord
from ..utils import get_protected_related_objects


class ProtectedResourceMixin(object):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as pe:
            protected_instances = list(get_protected_related_objects(instance))
            num_protected_instances = len(protected_instances)
            protected_instance_displays = [str(pi) for pi in protected_instances]

            model_name = (
                self.model_display_name or self.queryset.model.__class__.__name__
            )
            msg = "Cannot delete '{}' because " "it is referenced by {} {}.".format(
                model_name,
                num_protected_instances,
                pluralize(num_protected_instances, "record,records"),
            )

            msg += " [" + ", ".join(protected_instance_displays) + "]"
            return Response(msg, status=status.HTTP_403_FORBIDDEN)


class UpdatesMixin(object):
    def compress(self, added, modified, removed):
        added_lookup = {str(a["id"]): ts for ts, a in added}
        modified_lookup = {str(m["id"]): ts for ts, m in modified}
        removed_lookup = {str(r["id"]): ts for ts, r in removed}

        compressed_added = []
        for rec_timestamp, rec in added:
            pk = str(rec["id"])
            if pk in removed_lookup and rec_timestamp <= removed_lookup[pk]:
                continue
            compressed_added.append(rec)

        compressed_modified = []
        for rec_timestamp, rec in modified:
            pk = str(rec["id"])
            if pk in added_lookup or (
                pk in removed_lookup and rec_timestamp <= removed_lookup[pk]
            ):
                continue
            compressed_modified.append(rec)

        compressed_removed = []
        for rec_timestamp, rec in removed:
            pk = str(rec["id"])
            if (pk in added_lookup and rec_timestamp < added_lookup[pk]) or (
                pk in modified_lookup and rec_timestamp < modified_lookup[pk]
            ):
                continue
            compressed_removed.append(rec)

        return compressed_added, compressed_modified, compressed_removed

    def apply_query_param(self, query_params, key, value):
        if value is not None:
            query_params[key] = value

    def get_update_timestamp(self, request):
        qp_timestamp = request.query_params.get("timestamp")
        if qp_timestamp is None:
            return HttpResponseBadRequest()

        try:
            timestamp = parse_datetime(qp_timestamp)
        except ValueError:
            timestamp = None

        if timestamp:
            timestamp = timestamp.replace(tzinfo=pytz.utc)

        return timestamp

    def get_updates(self, request, *args, **kwargs):
        added = []
        modified = []
        removed = []

        timestamp = self.get_update_timestamp(request)
        pk = request.query_params.get("pk")

        serializer = self.get_serializer_class()

        qry = None
        added_filter = dict()
        updated_filter = dict()
        removed_filter = dict(app_label="api")

        self.apply_query_param(added_filter, "created_on__gte", timestamp)
        self.apply_query_param(updated_filter, "created_on__lt", timestamp)
        self.apply_query_param(updated_filter, "updated_on__gt", timestamp)
        self.apply_query_param(removed_filter, "created_on__gte", timestamp)

        self.apply_query_param(added_filter, "pk", pk)
        self.apply_query_param(updated_filter, "pk", pk)
        self.apply_query_param(removed_filter, "record_pk", pk)

        if hasattr(self, "limit_to_project"):
            qry = self.limit_to_project(request, *args, **kwargs)
        else:
            qry = self.filter_queryset(self.get_queryset())

        if hasattr(qry, "model"):
            removed_filter["model"] = qry.model._meta.model_name

        context = {"request": self.request}
        added = []
        added_records = qry.filter(**added_filter)
        for added_record in added_records:
            timestamp = added_record.updated_on
            serialized_rec = serializer(added_record, context=context).data
            added.append((timestamp, serialized_rec))

        modified = []
        modified_recs = qry.filter(**updated_filter)
        for modified_rec in modified_recs:
            timestamp = modified_rec.updated_on
            serialized_rec = serializer(modified_rec, context=context).data
            modified.append((timestamp, serialized_rec))

        removed = [
            (ar.created_on, dict(id=ar.record_pk, timestamp=ar.created_on))
            for ar in ArchivedRecord.objects.filter(**removed_filter)
        ]

        return added, modified, removed

    @action(detail=False, methods=["GET"])
    def updates(self, request, *args, **kwargs):
        added, modified, removed = self.get_updates(request, *args, **kwargs)
        added, modified, removed = self.compress(added, modified, removed)
        return Response(dict(added=added, modified=modified, removed=removed))


# Use this to override DRF DEFAULT_AUTHENTICATION_CLASSES (in settings) from ViewSet for specific methods
# Avoids 401s for unprotected endpoints -- but 403s (permissions classes) unaffected
class MethodAuthenticationMixin(object):
    # method_authentication_classes = {
    #     "OPTIONS": None,
    #     "GET": None,
    #     "POST": None,
    #     "PUT": None,
    #     "PATCH": None,
    #     "HEAD": None,
    #     "DELETE": None,
    #     "TRACE": None,
    #     "CONNECT": None,
    # }

    def initialize_request(self, request, *args, **kwargs):
        parser_context = self.get_parser_context(request)

        method = request.method.upper()
        if hasattr(self, "method_authentication_classes") and isinstance(
            self.method_authentication_classes.get(method), (list, tuple)
        ):
            authenticators = [
                auth() for auth in self.method_authentication_classes[method]
            ]
        else:
            authenticators = self.get_authenticators()

        return Request(
            request,
            parsers=self.get_parsers(),
            authenticators=authenticators,
            negotiator=self.get_content_negotiator(),
            parser_context=parser_context,
        )


class OrFilterSetMixin(object):

    def str_or_lookup(self, queryset, name, value, key=None, lookup_expr="iexact"):
        if not isinstance(name, (list, set, tuple)):
            name = [name]
        q = Q()
        for n in name:
            fieldname = "{}__{}".format(n, lookup_expr)
            for v in set(value):
                if v is not None and v != "":
                    predicate = {fieldname: str(v).strip()}
                    if key is not None:
                        predicate = {fieldname: [{key: str(v).strip()}]}
                    q |= Q(**predicate)
        print(q)
        return queryset.filter(q).distinct()

    def id_lookup(self, queryset, name, value):
        return self.str_or_lookup(queryset, name, value)

    def char_lookup(self, queryset, name, value):
        return self.str_or_lookup(queryset, name, value, lookup_expr="icontains")

    def json_id_lookup(self, queryset, name, value):
        return self.str_or_lookup(queryset, name, value, "id", "contains")

    def json_name_lookup(self, queryset, name, value):
        return self.str_or_lookup(queryset, name, value, "name", "contains")
