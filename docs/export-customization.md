# Export Customization

Status: partially implemented.

Export headers and row shaping live in `apps/api/app/exports/rows.py`. Workbook generation lives in `apps/api/app/exports/xlsx_export.py`.

Next customization step:

- Move widths, title rows, number formats and status highlighting into a template configuration object.
- Add institution-specific workbook templates without changing financial calculations.
- Keep CSV stable and raw even when XLSX styling changes.

