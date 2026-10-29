Authentication
==============

MERMAID secures its API in two ways, for two different kinds of client:

- **Writing a script, notebook, or any other code that talks to the API?** Use an `API key`_. It is the simplest option, and does not expire every few hours like a JWT does, so it is almost always what you want.
- **Building an interactive application where a person signs in through a browser?** Use `OAuth2 tokens`_ instead; an API key cannot be used to complete a browser login.

Either way, you first need a MERMAID account.


1. Create a MERMAID Account
---------------------------

Before you can request a token or an API key, you must first create a MERMAID user account. If you already have an account, skip ahead to whichever of the two sections above applies to you. If not, an account can be created at https://app.datamermaid.org/.


2. API keys
-----------

.. _`API key`:

An API key is a long-lived credential for scripts, notebooks and other machine clients that cannot complete a browser login. A key acts as the user who created it: every request it authenticates has exactly the projects and roles that user has, and loses access the moment a project membership is removed. It does **not** have its own, separate scope — anyone holding the key can do anything its creator's account can do, so treat it like a password and store it accordingly (an environment variable or secret manager, not source control).

Keys are managed at ``/apikeys/`` (see `Non-Project resources`) while signed in with a normal token; creating and revoking a key is the one thing a key cannot be used for itself (see below), so this step always needs a real, browser-based login. Any MERMAID account can create keys for itself; no special role is needed. Creating a key returns the key itself once, in the ``key`` field of the response. It is not stored and cannot be shown again, so copy it straight away. A key expires one year after it is created unless another expiry, or ``never_expires``, is given when it is created.

The key is sent in the same header as a token, and never in the URL:

::

    curl --request GET \
        --url https://api.datamermaid.org/v1/projects/ \
        --header 'Authorization: Bearer mmd_prod_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_...'

A key cannot be used to list, create or revoke API keys; that always requires a signed-in user. This means a leaked key cannot be used to issue itself a replacement or extend its own life.

.. _`Non-Project resources`: nonproject.html#apikeys


3. OAuth2 tokens
----------------

.. _`OAuth2 tokens`:

For an interactive application where a person signs in through a browser, use a JSON Web Token (JWT) instead of an API key.


`OAuth2 Implicit grant type`_ is used to fetch a valid token that can be used to securely access MERMAID API. The setup is shared by every application built against MERMAID:

    - Authorization URL: ``https://datamermaid.auth0.com/authorize``
    - Client ID: contact us at https://datamermaid.org/contact-us/ for this value
    - Audience: ``https://api.datamermaid.org``

For it to work we will also need the domain(s) your app will redirect to after login. Contact the MERMAID team at https://datamermaid.org/contact-us/ to request adding those domains.
.. _`OAuth2 Implicit grant type`: https://oauth.net/2/grant-types/implicit/

When making requests to the API, send the token in the ``Authorization`` request header:

::

    curl --request GET \
        --url https://api.datamermaid.org/v1/projects/ \
        --header 'Authorization: Bearer <VALID TOKEN HERE>'

Tokens in the URL query string (``?access_token=``) are not accepted: URLs are
recorded in server, load balancer and error-tracking logs.
