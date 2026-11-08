# Monthly reports

Reportes uses completed calendar months in the business timezone. The online sales
projection reuses Sales/Home Payment and PaymentRefund records, grouped by order
creation. Current known refunds revise older months; this is not a month-end cash
ledger. Fully refunded orders remain paid orders. Cash and simulated payments are
excluded. Average is net divided by distinct paid orders, rounded to currency units.

Saved JSON revisions back both authenticated UI and one-page PDF. Refresh checks
current finance/growth membership before calculation and again before save.
Business and report ID must both match. Existing schemas require explicit offline
`monthly_reports.migrate(engine)` before this feature can open; fresh schemas include
its table. No customer contact fields are saved in reports.

The optional `app.state.monthly_website_reader(request,business,span)` is installed
by the root provisioning composition. No sample analytics fallback exists. It returns
status, values and factual coverage. Legacy tracking activation is unknown; first
retained Umami event is labeled data availability. Google monthly history is absent.

No-order historical periods have unknown coverage, not a measured zero. Existing
confirmed records remain useful but their historical completeness is unverified.
Snapshots retain this gap. Campaign activity is live-scope accepted dispatch and
non-scanner visits; sales require canonical unique order credits plus paid payments.

Implementation files: sales_metrics.py, workspace_period.py, sales_workspace.py,
workspace_overview.py, monthly_reports.py, monthly_report_pdf.py, db.py, api.py,
customer_workspace.py; frontend monthly-reports.tsx/css, main.tsx and sales.tsx.
ReportLab5.1.0 renders embedded Inter derived from the existing licensed font.

Validation uses isolated completed-month fixtures and retained runtime records
separately. Never backdate the actual demo or call simulated payments real revenue.
