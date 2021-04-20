Project resources
=================

Project-related resources in MERMAID all begin, relative to the API root, with ``/projects/<project_id>/``, where ``<project_id>`` is the UUID of a project. See :doc:`getting_started` for how to determine a ``project_id`` manually, or use the API to retrieve a list of project ids to which a user has access using the :ref:`projects_resource` resource.

Data access
-----------

All data access in MERMAID is based on projects. No top-down organizational hierarchy or ACL logic is used; rather,
any user may create a new project and add any other MERMAID user to it. The concept of "organization" exists; a project may be associated with any number of organizations, as tags, useful for filtering but not access control.

Authenticated access to project data depends on the association of a user profile with a project, in different roles. Generally, the permissions associated with these roles govern access to the Project resources specified on this page.

Unauthenticated access to project data depends on the data sharing policies chosen per survey method for a project. Generally, these policies govern access to :ref:`aggregated views <data_sharing>`, not the Project resources specified here, which all require authentication and project membership.

All resources specified on this page support: ``GET``, ``PUT``, ``PATCH``, ``POST``, ``DELETE``, ``HEAD``, ``OPTIONS`` except as noted for sample unit methods.

Roles
^^^^^

Authenticated access to project data depends on the association of a user profile with a project, in one of three roles:

- **admin** [90]: User has all permissions for project, including removing other (potentially admin) users. A user is an admin on any project they create.
- **collector** [50]: User may create/update/delete CollectRecords (unsubmitted sample units), sites, and management regimes, and may create ("suggest") benthic attributes and fish species. All other permissions are read-only.
- **read-only** [10]: User may read all data for project, but may not create, update, or delete anything.

Project entity resources
------------------------

/projects/<project_id>/sites/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All sites for a project.

/projects/<project_id>/managements/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All management regimes for a project.

/projects/<project_id>/project_profiles/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All user profiles for a project. Note a given CollectRecord (unsubmitted sample unit) is associated with a user profile, and in the MERMAID frontend is only available to that user. Note also that though a ``project_profile`` has an ``id``, ``project_profile.profile`` is the id of the user profile associated with the project.

/projects/<project_id>/observers/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An ``observer`` is a relationship between a user ``profile`` and a sample unit method; a given sample unit method may have multiple observers, and the profile associated with a CollectRecord may or may not be one of the profiles of those observers. Note also that though an ``observer`` has an ``id``, ``observer.profile`` is the id of the user profile associated with the observer.

/projects/<project_id>/collectrecords/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See :doc:`collectrecords` for more detail.

A ``CollectRecord`` is a nested JSON representation of all the objects and values that together represent an unsubmitted sample unit for a project. A ``GET`` request to this resource returns the CollectRecords created by the user, unless the ``showall`` query parameter is used to return projects unfiltered by the user's membership.

| `Permissions`: Regular project-based permissions apply, but only the user who created a CollectRecord may use the ``validate`` and ``submit`` routes.
| `Additional routes`:

- ``validate/`` (``POST``): Runs all relevant validations for a CollectRecord, stores those validations in the CollectRecord itself, and returns them in the response.
- ``submit/`` (``POST``): Submits CollectRecord, i.e. attempts to store all the component parts of the unsubmitted sample unit in the correct places. Runs validations as part of submission.

Observations
------------

Observation resources are the lowest level of MERMAID data, representing individual observations in sample unit methods, which belong to sample events (a set of sample unit methods at a particular site on a particular date).

/projects/<project_id>/obstransectbeltfishs/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Belt fish transect observations. Filters:

- ``beltfish``
- ``beltfish__transect``
- ``beltfish__transect__sample_event``
- ``fish_attribute``
- ``size_min``/``size_max``
- ``count_min``/``count_max``

/projects/<project_id>/obsbenthiclits/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Benthic LIT observations. Filters:

- ``benthiclit``
- ``benthicpit__transect``
- ``benthiclit__transect__sample_event``
- ``attribute``
- ``growth_form``
- ``length_min``/``length_max``

/projects/<project_id>/obsbenthicpits/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Benthic PIT observations. Filters:

- ``benthicpit``
- ``benthicpit__transect``
- ``benthicpit__transect__sample_event``
- ``attribute``
- ``growth_form``

/projects/<project_id>/obshabitatcomplexities/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Habitat complexity observations. Filters:

- ``habitatcomplexity``
- ``habitatcomplexity__transect``
- ``habitatcomplexity__transect__sample_event``
- ``score`` (lookups in ``habitatcomplexityscores`` object from :ref:`choices` resource)

/projects/<project_id>/obscoloniesbleached/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Observations of number of coral colones bleached for a quadrat collection. Simple equality filters are available for every field.

/projects/<project_id>/obsquadratbenthicpercent/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Observations of percent cover for hard coral, soft coral, and algae for each quadrat in a quadrat collection. Simple equality filters are available for every field.

Sample units
------------

In MERMAID, what are often referred to as "sample units" or "transects" are in fact "sample unit method" instances -- applications of a survey methodology to a physical transect or quadrat collection. The latter are actual "sample units". Thus, a single benthic transect might be associated with a benthic PIT, benthic LIT, or habitat complexity transect method. These endpoints are rarely employed by themselves.

The only useful filters are likely to be ``len_surveyed_min``/``len_surveyed_max`` for ``fishbelttransects`` and ``benthictransects``.

/projects/<project_id>/fishbelttransects/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/benthictransects/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/quadratcollections/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample unit methods
-------------------

Sample unit methods are not directly creatable; they are created when a request is made to the :doc:`collectrecords` ``submit/`` route, after having passed validation. They have no filters. The body of a ``PUT`` request for updating a sample unit method is the same as that of a CollectRecord.

Methods: ``GET``, ``PUT``, ``HEAD``, ``DELETE``

/projects/<project_id>/beltfishtransectmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/benthiclittransectmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/benthicpittransectmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/habitatcomplexitytransectmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/bleachingquadratcollectionmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

/projects/<project_id>/sampleunitmethods/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample events
-------------

A sample event in MERMAID is a unique combination of site, management regime (both of which are specific to a project), and sample date. It represents all observations from all sample units (of whatever type) collected at a place on a date.

/projects/<project_id>/sampleevents/
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Filters:

- ``sample_date_before``/``sample_date_after``
