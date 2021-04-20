Authentication
==============

MERMAID uses OAuth2 authentication for securing and accessing the MERMAID API's secure endpoints.  The following steps are required before making requests to the API:


1. Create a MERMAID Account
---------------------------

Before you can make a request for a JSON Web Token (JWT) or accessing the API, you must first create a MERMAID user account.  If you already have an account jump to section 2, if not, an account can be created at https://collect.datamermaid.org/.


2. Requesting Tokens
--------------------

`OAuth2 Implicit grant type`_ is used to fetch a valid token that can be used to securely access MERMAID API.  The folowing details will be needed to setup an implicit authorization flow:

    - Authorization URL
    - Redirect URL
    - Client ID
    - Audience

These details can be requested from the MERMAID team at https://datamermaid.org/contact/.

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
