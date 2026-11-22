# Analysis outputs

```text
outputs/
├── charts/   # SVG source charts and PNG images for Feishu
├── tables/   # CSV data tables
└── README.md
```

## Charts

Upload the PNG files from `charts/` to Feishu one at a time. Keep the matching SVG files as source versions.

- `purchase_rate_bar.png`: visitor type purchase rates; section 2.1.1.
- `purchase_rate_difference.png`: new visitor minus returning visitor, in percentage points; section 2.1.1.
- `visitor_sessions.png`: session counts by visitor type; section 1.3.2.

## Tables

- `tables/purchase_rate_by_visitor.csv`: sessions, purchases, and purchase rates.
- `tables/data_quality_summary.csv`: dataset size, missing values, duplicates, and ProductRelated range.
- `tables/missing_values_by_field.csv`: missing count for each field.

Rerun the analysis:

```bash
.venv/bin/python src/analyze_shoppers.py
```

This refreshes the CSV tables and SVG source charts. Re-export the PNGs if the chart data changes.
