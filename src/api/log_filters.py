import logging


class IgnoreGDALJSONParseErrors(logging.Filter):
    """
    GDAL logs (rather than raises) JSON parse errors on malformed geometry
    input before Django raises GDALException, which request validation turns
    into a 400. Drop those records so they don't reach the admin emails.
    """

    def filter(self, record):
        msg = record.getMessage()
        return not (msg.startswith("GDAL_ERROR") and "JSON parsing error" in msg)
