High-level MERMAID API documentation
====================================

The MERMAID API is the central interface through which all MERMAID data is read and written, and is the core of the `MERMAID project <https://datamermaid.org/>`_, which seeks to accelerate coral reef conservation by making common coral reef data collection and analysis fast, less error-prone, secure, and flexible.

This documentation refers to its production instantiation at https://api.datamermaid.org/v1/, backed by an AWS-based
stack including an RDS PostgreSQL database and using `Django <https://www.djangoproject.com/>`_ and
`Django REST Framework <https://www.django-rest-framework.org/>`_, and is actively used by

* `MERMAID collection app <https://collect.datamermaid.org>`_ [`repository <https://github.com/data-mermaid/mermaid-collect>`__]
* `MERMAID public dashboard <https://dashboard.datamermaid.org/>`_ [`repository <https://github.com/data-mermaid/mermaid-dash>`__]
* `mermaidr <https://github.com/data-mermaid/mermaidr>`_ analysis package

Our code is free (`as in speech <https://www.gnu.org/philosophy/free-sw.en.html>`_) and `open source <https://github.com/data-mermaid/>`_.

.. note::
   This documentation is for folks who know how to use `API <https://en.wikipedia.org/wiki/API>`_\s. If you are not a developer and just want to access your MERMAID data for analysis, go to
   `mermaidr <https://github.com/data-mermaid/mermaidr>`_ and read the excellent documentation there.


.. toctree::
   :maxdepth: 1
   :caption: Getting started

   getting_started
   authentication

.. toctree::
   :maxdepth: 1
   :caption: Resources

   nonproject
   projects
   collectrecords
   aggregated

.. toctree::
   :maxdepth: 1
   :caption: Developers

   developer
   contributing
