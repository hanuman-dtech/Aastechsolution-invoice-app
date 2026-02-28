# Session Changelog (Latest Stabilization)

This document summarizes notable functional updates from the recent stabilization cycle.

## Highlights

- Normalized backend API prefix to `/api`.
- Added/updated frontend path alignment for invoice and SMTP actions.
- Improved invoice generation payload/result alignment between frontend and backend.
- Added wizard option to allow duplicate invoice generation when explicitly requested.
- Added customer-specific payment terms support in customer create/update flows.
- Auto-provisioned default contract/schedule on customer creation.
- Improved contractor/client labeling consistency in email and PDF rendering.
- Added vendor and SMTP edit flows in frontend pages.
- Added customer-name fallback mapping in invoice list rendering.

## Deployment status notes

- Docker stack build/start executed successfully in latest run.
- Services reported up; post-start readiness checks should always be verified after each deployment.

## Next recommended follow-up

- Add CI automation for lint/type/build + API smoke checks.
- Add integration tests for generation modes and schedule behavior.
- Add auth hardening and role-based endpoint protection if required for production.
