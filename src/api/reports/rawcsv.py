import json
import re
import unicodecsv as csv
from operator import itemgetter
from rest_framework.utils import encoders
from collections import Mapping

from . import BaseReport
from ..utils.flatten_dict import flatten
from ..utils import is_match


class Echo(object):
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class RawCSVReport(BaseReport):

    def __init__(self, *args, **kwargs):
        # Columns to exclude from report
        self.excluded_columns = kwargs.get('excluded_columns') or []

    @property
    def media_type(self):
        return 'text/csv'

    def _get_table_data(self, data_iter, serializer_class, *args, **kwargs):
        serialized_data = list(serializer_class(data_iter).data)
        if 'order_by' in kwargs:
            serialized_data = sorted(serialized_data, key=itemgetter(*kwargs['order_by']))
        header = [f.display for f in serializer_class.get_fields()]
        header = self._apply_excluded_columns(header)
        return header, serialized_data

    def _flatten_record(self, record_dict):
        return flatten(
            json.loads(json.dumps(record_dict, cls=encoders.JSONEncoder))
        )

    def _concat_lists(self, flat_record):
        for k, v in flat_record.iteritems():
            if isinstance(flat_record[k], (list, set, tuple,)) and len(flat_record[k]) > 0:
                if isinstance(flat_record[k][0], Mapping):
                    continue

                flat_record[k] = ','.join([str(e) for e in v])
            else:
                flat_record[k] = v

        return flat_record

    def _apply_excluded_columns(self, header):
        patterns = [re.compile(c) for c in self.excluded_columns]
        return [c for c in header
                if is_match(c, patterns) is False]

    def _apply_formatters(self, flat_record):
        return self._concat_lists(flat_record)

    def stream(self, data, serializer_class, *args, **kwargs):
        header, flat_data = self._get_table_data(
            data,
            serializer_class,
            *args,
            **kwargs
        )
        csv_buffer = Echo()
        csv_writer = csv.DictWriter(csv_buffer,
                                    fieldnames=header,
                                    extrasaction='ignore')
        yield csv_buffer.write('{}\n'.format(','.join(header)))
        for flat_record in flat_data:
            yield csv_writer.writerow(self._apply_formatters(flat_record))

    def generate(self, path, data, serializer_class, *args, **kwargs):
        header, flat_data = self._get_table_data(
            data,
            serializer_class,
            *args,
            **kwargs
        )

        with file(path, 'wb') as csvfile:
            csv_writer = csv.DictWriter(csvfile,
                                        fieldnames=header,
                                        extrasaction='ignore')
            csv_writer.writeheader()
            for flat_record in flat_data:
                csv_writer.writerow(self._apply_formatters(flat_record))
