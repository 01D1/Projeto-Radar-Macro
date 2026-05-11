# Phase 2: Reliable Data Ingestion — Discussion Log

**Date:** 2026-05-10
**Areas covered:** 4 of 4

---

## Area 1: news_hunter/ Integration Depth

**Q1:** How deep should news_hunter/ be integrated into src/?
- Options: Subprocess bridge / Shared SQLite only / Full refactor into src/ingestion/
- **Selected:** Subprocess bridge
- Note: Fast, safe, preserves working system. Full refactor deferred to Phase 5.

**Q2:** Scheduling: src/scheduler takes over or both run in parallel?
- Options: src/scheduler takes over / Both run in parallel
- **Selected:** src/scheduler takes over
- Note: Disable news_hunter/agendador.py. Single scheduler, single run_id.

---

## Area 2: SQLite Schema Design

**Q1:** Unified SQLite DB or keep file-based storage?
- Options: New unified ingestion DB / Keep files + add metadata sidecar
- **Selected:** New unified ingestion DB (data/ingestion.db, 4 tables)

**Q2:** Does news_hunter/banco.db migrate into ingestion.db?
- Options: Stay separate / Migrate into ingestion.db
- **Selected:** Stay separate
- Note: src/ reads news from banco.db via SQL; no migration risk.

---

## Area 3: CVM Raw Format

**Q1:** CVM XML vs CSV (ING-01 says "raw XML preserved")?
- Options: Keep CSV relabel as raw / Switch to XML / Store both
- **Selected:** Keep CSV, relabel as raw
- Note: ING-01 "XML" was aspirational. CSV from ZIP covers all required fields.

**Q2:** Watchlist-only extraction or store full ZIP?
- Options: Watchlist-only extraction / Store full ZIP
- **Selected:** Watchlist-only extraction
- Note: Lean data/raw/cvm/. Re-extract on ticker add, re-download only if ZIP not cached.

---

## Area 4: BCB SGS Porting Strategy

**Q1:** Lift-and-adapt from pipeline banco completo/ or write fresh?
- Options: Lift-and-adapt / Write fresh
- **Selected:** Lift-and-adapt
- Note: Extract API fetch pattern from 03_coletor_macro.py. Apply @retry + IngestionError.

**Q2:** Freshness threshold for stale warning?
- Options: >1 business day / >3 days
- **Selected:** >1 business day
- Note: Use pandas_market_calendars BMFBOVESPA. Log WARNING (not ERROR) for stale.

---

## Claude's Discretion Items

- `ingestion.db` table schema column names — standard snake_case, ISO strings for dates
- IPE PDF extraction library choice — pdfplumber or PyMuPDF (research phase decides)
- BCB CDS Brazil fallback source if BCB SGS doesn't carry it (ANBIMA or ipeadata)
- sqlite3 vs sqlite-utils for raw DB access — researcher to recommend

---

*Discussion conducted: 2026-05-10*
*CONTEXT.md written: .planning/phases/02-reliable-data-ingestion/02-CONTEXT.md*
