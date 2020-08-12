# import zipfile
# from datetime import datetime
# from io import BytesIO
# from typing import Iterable

# from django.core.exceptions import ObjectDoesNotExist
# from django.http import HttpResponseBadRequest, StreamingHttpResponse, HttpResponse
# from django.utils.text import get_valid_filename

# from api.models import Project
# from api.reports import RawCSVReport


# def fieldreport(obj, request, *args, **kwargs):
#     serializer_class = kwargs.get("serializer_class")
#     model_cls = kwargs.get("model_cls")
#     fk = kwargs.get("fk")
#     order_by = kwargs.get("order_by")

#     try:
#         project = Project.objects.get(pk=kwargs["project_pk"])
#     except ObjectDoesNotExist:
#         return HttpResponseBadRequest("Project doesn't exist")

#     serializer_classes = _set_to_list(serializer_class)
#     model_classes = _set_to_list(model_cls)
#     if len(serializer_classes) != len(model_classes):
#         raise ValueError("Number of serializer_class and model_cls do not match")

#     obj.limit_to_project(request, *args, **kwargs)
#     qs = obj.get_queryset()
#     transect_ids = [rec.id for rec in obj.filter_queryset(qs).iterator()]
#     ts = datetime.utcnow().strftime("%Y%m%d")
#     projname = get_valid_filename(project.name)[:100]
#     modelname = fk
#     if fk in ("id", "fk",):
#         modelname = model_cls._meta.model_name or fk

#     if len(serializer_classes) == 1:
#         ext = "csv"
#         obls = model_cls.objects.filter(**{f"{fk}": project.pk})
#         # obls = model_cls.objects.filter(**{"%s__in" % fk: transect_ids})
#         fields = [f.display for f in serializer_class.get_fields()]
#         serialized_data = serializer_class(obls).get_serialized_data(order_by=order_by)
#         report = RawCSVReport()
#         stream = report.stream(fields, serialized_data)
#         response = StreamingHttpResponse(stream, content_type="text/csv")

#     else:
#         ext = "zip"
#         streams = []
#         for sc, mdl in zip(serializer_classes, model_classes):
#             obls = mdl.objects.filter(**{"%s__in" % fk: transect_ids})
#             fields = [f.display for f in sc.get_fields()]
#             serialized_data = sc(obls).get_serialized_data(order_by=order_by)
#             report = RawCSVReport()
#             streams.append(report.stream(fields, serialized_data))

#         inmem_file = BytesIO()
#         zipped_reports = zipfile.ZipFile(
#             inmem_file, "w", compression=zipfile.ZIP_DEFLATED
#         )

#         for mdl, stream in zip(model_classes, streams):
#             file_name = "{}-{}-{}.csv".format(
#                 projname, mdl.__name__.lower(), ts
#             )
#             content = "".join(list(stream))
#             zipped_reports.writestr(file_name, content)
#         zipped_reports.close()
#         inmem_file.seek(0)

#         response = HttpResponse(
#             inmem_file.read(), content_type="application/octet-stream"
#         )

#     response["Content-Disposition"] = 'attachment; filename="{}-{}-{}.{}"'.format(
#         modelname, projname, ts, ext
#     )

#     return response


# def _set_to_list(obj):
#     if isinstance(obj, Iterable):
#         return obj
#     return [obj]