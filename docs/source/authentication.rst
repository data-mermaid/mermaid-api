Authentication
==============

MERMAID uses OAuth2 authentication for securing and accessing the MERMAID API's secure endpoints. Scripts and other machine clients can use an `API key`_ instead. The following steps are required before making requests to the API:


1. Create a MERMAID Account
---------------------------

Before you can make a request for a JSON Web Token (JWT) or accessing the API, you must first create a MERMAID user account.  If you already have an account jump to section 2, if not, an account can be created at https://app.datamermaid.org/.


2. Requesting Tokens
--------------------

`OAuth2 Implicit grant type`_ is used to fetch a valid token that can be used to securely access MERMAID API.  The folowing details will be needed to setup an implicit authorization flow:

    - Authorization URL
    - Redirect URL
    - Client ID
    - Audience

These details can be requested from the MERMAID team at https://datamermaid.org/contact-us/.

.. _`OAuth2 Implicit grant type`: https://oauth.net/2/grant-types/implicit/


3. Calling API
--------------

When making requests to the API the token can be included in:

- the request header

::

    curl --request GET \
        --url https://api.datamermaid.org/projects/ \
        --header 'Authorization: Bearer <VALID TOKEN HERE>'


- the url query string

::

    https://api.datamermaid.org/projects/?access_token=<VALID TOKEN HERE>


4. API keys
-----------

.. _`API key`:

An API key is a long-lived credential for scripts, notebooks and other machine clients that cannot complete a browser login. A key acts as the user who created it: every request it authenticates has exactly the projects and roles that user has, and loses access the moment a project membership is removed.

Keys are managed at ``/apikeys/`` (see `Non-Project resources`) while signed in with a normal token. Creating a key returns the key itself once, in the ``key`` field of the response. It is not stored and cannot be shown again, so copy it straight away. A key expires one year after it is created unless another expiry, or ``never_expires``, is given when it is created.

The key is sent in the same header as a token, and never in the URL:

::

    curl --request GET \
        --url https://api.datamermaid.org/v1/projects/ \
        --header 'Authorization: Bearer mmd_prod_xxxxxxxxxxxx_...'

A key cannot be used to list, create or revoke API keys; that always requires a signed-in user.

.. _`Non-Project resources`: nonproject.html#apikeys
