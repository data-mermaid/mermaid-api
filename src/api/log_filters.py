import logging

BENIGN_GDAL_INPUT_ERRORS = (
    "JSON parsing error",
    "Unsupported geometry type detected",
)


class IgnoreGDALJSONParseErrors(logging.Filter):
    """
    GDAL logs (rather than raises) errors on malformed or unsupported geometry
    input (e.g. JSON parse errors, unsupported geometry types) before Django
    raises GDALException, which request validation turns into a 400. Drop
    those records so they don't reach the admin emails or Sentry.
    """

    def filter(self, record):
        msg = record.getMessage()
        return not (
            msg.startswith("GDAL_ERROR")
            and any(s in msg for s in BENIGN_GDAL_INPUT_ERRORS)
        )
