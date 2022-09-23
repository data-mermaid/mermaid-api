SELECT 'CREATE DATABASE mermaid'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mermaid')\gexec
