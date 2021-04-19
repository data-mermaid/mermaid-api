Aggregated views
================

MERMAID aggregated views are convenience resources that roll up many lookups and aggregate data at various levels with standardized calculations of common indicators, such as biomass. All aggregated views are read-only (i.e., support only ``GET`` requests). As with regular :doc:`projects`, aggregated view resources in MERMAID all begin, relative to the API root, with ``/projects/<project_id>/``, where ``<project_id>`` is the UUID of a project. See :doc:`getting_started` for how to determine a ``project_id`` manually, or use the API to retrieve a list of project ids to which a user has access using the :ref:`projects_resource` resource.

All views will return data in one of three formats:

- ``.../`` (i.e., default) or ``.../json/``: standard `JSON <https://www.json.org/json-en.html>`_, with ``content-type`` = ``application/json``
- ``.../csv/``: comma-separated 2D matrix (some fields are JSON)
- ``.../geojson/``: returns `GeoJSON <https://geojson.org/>`_ suitable for loading into a GIS

Filters

.. _data_sharing:

Data sharing policies
---------------------

Access to project data for all unauthenticated requests is based on the data sharing policy attached to each survey method for that project. Each survey method (e.g., fish belt transect) may be assigned one of three policies: ``private``, ``public summary`` (default), and ``public``. The three policies are summarized in the table below.

how policies translate into aggregated view permissions

.. image:: _static/MERMAID-data-policy-draft-April2019.png

Observation views
-----------------

asdf

Sample Unit views
-----------------

asdf

Sample Event views
------------------

as

Site summary view
-----------------

dfg
