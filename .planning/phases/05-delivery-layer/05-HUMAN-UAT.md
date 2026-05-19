---
status: complete
phase: 05-delivery-layer
source: [05-VERIFICATION.md]
started: 2026-05-18T18:00:00Z
updated: 2026-05-18T18:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Watchlist page renders correctly
expected: Color-coded st.dataframe with thesis tickers; Posicionamento column shows green/yellow/red badges; Upside % shows +/- formatted values; freshness caption at bottom
result: PASS

### 2. Asset Detail page — selectbox + PDF download
expected: Three st.metric columns (Posicionamento/Valor Justo/Upside), expandable Driver and Risco cards, PDF download button visible; clicking download produces a valid PDF file
result: PASS

### 3. Macro Panel page renders Plotly dark charts
expected: Selic chart full-width, IPCA+PTAX in 2-col row 2, CDS+PIB in 2-col row 3 — all with plotly_dark theme and #93C5FD line color
result: PASS

### 4. Opportunities page renders signal cards
expected: Signal cards with ticker bold, description, signal_type badge (blue/yellow/navy), st.progress bar for conviction score
result: PASS

### 5. Telegram positioning-change alert fires
expected: Alert contains ticker in bold, old→new positioning, confidence, one-line rationale, top opportunity
result: PASS

### 6. Morning brief delivered at 08:15 weekday
expected: Telegram message with date header, Selic/PTAX/IBOV values, up to 3 top movers
result: PASS

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
