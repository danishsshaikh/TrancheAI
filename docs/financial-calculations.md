# Financial Calculations

Status: implemented in `apps/api/app/services/financials.py`.

Rules:

- Initial sanctioned amount is the sum of approved original sanctions.
- Approved increases add to sanctioned funding.
- Approved reductions subtract from sanctioned funding.
- Draft, rejected and cancelled records do not affect totals.
- Utilization is recorded separately from disbursement.
- Refunds reduce net disbursement.
- Negative balances are exposed as reconciliation states, never clamped to zero.

Validation is implemented in `apps/api/app/services/validation.py`.

Reconciliation checks are implemented in `apps/api/app/services/reconciliation.py`.

