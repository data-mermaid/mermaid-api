# From auth0: for a 'Client' (here: 'Demo CLI') accessing an 'API' (here: MERMAID API (Dev))
# client_id needs to be registered as an application with Django: https://dev-api.datamermaid.org/admin/api/application/
# Note that django application is associated with a user profile, which controls permissions
# This PoC uses dev settings that need to be replaced with production settings
client_id = 'EXAMPLE3cWeUEXAMPLEGwH5rZEXAMPLE'
client_secret = 'EXAMPLEhObfPwBEXAMPLEBB102qoEXAMPLE_pGorbzEXAMPLERmtXZOFNEXAMPLE'
project_name = 'My Project'

URL = 'https://datamermaid.auth0.com'
audience = 'https://api.datamermaid.org'
api = 'https://api.datamermaid.org/v1/'
params = {'format': 'json'}
grant_type = 'client_credentials'
