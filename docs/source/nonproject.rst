Non-Project resources
=====================

All resources not associated with particular projects are on the API root (in production, ``https://dev-api.datamermaid.org/v1/``).

General
-------

Except where noted otherwise:

| `Authentication`: not required
| `Methods`: ``GET``, ``HEAD``, ``OPTIONS``

/health/
^^^^^^^^

Returns ``ok`` unconditionally.

/version/
^^^^^^^^^

Returns current versions of registered apps -- currently ``collect`` and ``api``.

| `Authentication`: required

/me/
^^^^

Profile information for current user.

| `Authentication`: required
| `Permissions`: Only current user may access.
| `Methods`: ``GET``, ``PUT``
| `Additional routes`:

- ``change_password/`` (``POST``)

/profiles/
^^^^^^^^^^

List of user profiles. For privacy, only the ``id``\s of users are returned, without personally identifiable information.

/projecttags/
^^^^^^^^^^^^^

List of project tags ("organizations"). Read-only; new tags are created with `proposed` status via editing a project.

/sites/
^^^^^^^

List of project sites. Includes a ``validations`` item listing the results of the validation that ran the last time the site was validated.

`Additional filters`:

- ``exclude_projects``: comma-separated list of project ids
- ``unique``: returns list of sites not belonging to the provided project id that are a unique combination of ``name``, ``country_id``, ``reef_type_id``, ``reef_zone_id``, ``exposure_id``, ``location``

.. note::
    A site belongs to only one project. Two sites might have exactly the same attributes (other than ``id``) but are considered different sites.

/managements/
^^^^^^^^^^^^^

List of project management regimes. Includes a ``validations`` item listing the results of the validation that ran the last time the management regime was validated.

`Additional filters`:

- ``exclude_projects``: comma-separated list of project ids
- ``unique``: returns list of sites not belonging to the provided project id that are a unique combination of ``name``, ``country_id``, ``reef_type_id``, ``reef_zone_id``, ``exposure_id``, ``location``
- ``est_year_min``/``est_year_max``: earliest/latest year established

.. note::
    A management regime belongs to only one project. Two management regimes might have exactly the same attributes (other than ``id``) but are considered different management regimes.

Choices and attributes
----------------------

Choices and attributes provide most of the "lookup" entities that MERMAID transects and observations require. "Attributes" are "things that can be observed" -- coral and other taxa as well as nonorganic benthic substrates for benthic transects and bleaching surveys, fish species/genera/families as well as arbitrary fish groupings for fish belt transects, and so on.

All attributes have a filterable ``regions`` property that detail which of the 12
`MEOW <https://geospatial.tnc.org/datasets/ed2be4cf8b7a451f84fd093c2e7660e3_0?geometry=11.953%2C-89.110%2C-11.953%2C87.258>`_
regions the attribute belongs to.

All attributes also allow ``POST``, ``PUT``, and ``DELETE`` methods, where an authenticated user may use ``POST`` to suggest a new attribute (marked on creation as ``status=PROPOSED``), and edit/delete an existing attribute that has ``status=PROPOSED``.

.. _choices:

/choices/
^^^^^^^^^

Convenience resource that returns a list of objects, each one of which has a ``name`` item (e.g., ``countries``) and a ``data`` item that is a list of available choice objects.

`Additional routes`:

- ``updates/`` (``GET``): returns object of following form where items have changed since the passed ``timestamp`` parameter:

::

    {
      "added": [...],
      "modified": [...],
      "deleted": [...]
    }

/fishsizes/
^^^^^^^^^^^

Separate choice resource used only for looking up the actual size to record for a fish, given a particular fish size bin used for the survey.

/benthicattributes/
^^^^^^^^^^^^^^^^^^^

List of MERMAID benthic attributes. Includes nonorganic substrates like "rubble" as well as coral and other taxa.

/fishfamilies/
^^^^^^^^^^^^^^

List of MERMAID fish families. Biomass constants are the calculated means of all species belonging to each family.

/fishgenera/
^^^^^^^^^^^^

List of MERMAID fish genera. Biomass constants are the calculated means of all species belonging to each genus.

/fishspecies/
^^^^^^^^^^^^^

List of MERMAID fish species. Includes biomass constants and maximum observed length as well as useful analytical properties such as vulnerability score, trophic level, trophic group, and functional group.

/fishgroupings/
^^^^^^^^^^^^^^^

Fish groupings are arbitrary (but useful) groupings of fish species, genera, and families that are treated as a single taxon for purposes of observation and analysis (typically some form of "other"). As with fish genera and families, biomass constants and regions are calculated from member taxa; additionally, a ``fish_attributes`` property is returned listing each member species, genus, and family.

.. _projects_resource:

/projects/
----------

The projects resource at the root of the API, without query parameters, returns a list of projects of which the user is a member. The ``showall`` query parameter may be used to return projects unfiltered by the user's membership. ``showall`` is important when the user is unauthenticated.

| `Authentication`: required for ``PUT`` and ``POST`` requests.
| `Permissions`: Read-only when unauthenticated. To update, the user must be an ``admin`` for the project, unless they are using the ``find_and_replace_sites/`` or ``find_and_replace_managements/`` routes, in which case the user may be a project member of any non-readonly type.
| `Methods`: ``GET``, ``PUT``, ``POST``
| `Additional routes`:

- ``create_project/`` (``POST``): Create new project from request body, including all related project profiles, sites, and management regimes.
- ``updates/`` (``GET``): returns object of following form where items have changed since the passed ``timestamp`` parameter:

::

    {
      "added": [...],
      "modified": [...],
      "deleted": [...]
    }

- ``find_and_replace_sites/`` (``PUT``): Replace the site specified by the ``find`` query parameter associated with all submitted and unsubmitted sample units with the site specified by the ``replace`` query parameter, then delete the ``find`` site.
- ``find_and_replace_managements/`` (``PUT``): Replace the management regime specified by the ``find`` query parameter associated with all submitted and unsubmitted sample units with the management regime specified by the ``replace`` query parameter, then delete the ``find`` management regime.
- ``transfer_sample_units/`` (``PUT``): Associate every sample unit in the project with the profile specified by the ``from_profile`` query parameter with the profile specified by the ``to_profile`` query parameter.
