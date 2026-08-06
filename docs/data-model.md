# Data Model

Status: partially implemented.

Implemented entities:

- Project: one canonical innovation project.
- Project Participant: names and roles attached to a project.
- Funding Sanction: original approved funding.
- Funding Revision: increases, reductions and other revisions after sanction.
- Tranche: disbursement or payment activity attached to a project.
- Audit Event: traceability record for important operations.

Relationships:

- One project has many participants.
- One project has zero or more sanctions.
- One project has zero or more funding revisions.
- One project has zero or more tranches.
- Audit events reference entity type and entity id.

Production persistence is represented by SQLAlchemy models and Alembic migration `0001_initial`. Full migration execution is server verification required.

