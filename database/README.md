# Database Structure

This directory contains JSON schemas that define the structure of the system's records.

## Schemas

- `project.schema.json`: Structure for discovered projects and opportunities.
- `watchlist.schema.json`: Structure for projects, wallets, sources, and accounts that require continued monitoring.
- `evidence.schema.json`: Structure for claims, observations, and supporting evidence.

## Data Integrity Rules

- Validate records against the relevant schema before accepting them.
- Preserve original evidence and source references.
- Record timestamps for discovery and updates.
- Unknown information must remain unknown, not be treated as negative evidence.
- Never overwrite historical evidence when new information appears.
- Keep schema definitions separate from actual project and evidence records.

## Important

These schemas define data formats. They do not create a working database or automatically connect to external data sources. The system must implement storage, validation, and retrieval separately.
