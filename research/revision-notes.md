# Revision notes

## Scope

Translated and revised the article and glossary into English, added a TRIMP-focused audit and algorithm-release timeline, and regenerated the existing English-labelled figures with corrected claims. Raw CSVs and original analysis JSONs were retained. No live database access or changes were made in this revision. The project directory is not a Git repository; originals were copied before editing.

## Corrections that affect interpretation

- The Strain comparison uses an internal-load construct, not steps/calories as a criterion standard.
- Same-date workout correlation does not survive a calendar-alignment sensitivity check: previous-day workouts correlate strongly with Day Strain. All five tested lags and identical-date support are retained; no selected-lag correction is applied.
- WHOOP muscular load dates to the 2023 Strength Trainer release; 2026 expanded automatic estimation.
- Displayed HR zones and the proprietary Strain calculation are not identical. The October 2025 support article explicitly says manual zone changes do not directly change Strain.
- The original calibration exclusion omitted October 11–12 but retained October 8–9. Calibration status is unknown.
- The 0.05 autocorrelation label was based on a different cohort/row adjacency and did not establish white noise. The figure no longer calls the distribution noise.
- Missing workout entries are not confirmed rest days. The revised article does not report the old mixed-cohort rest/workout means.
- PostgreSQL footer records are now excluded by the current figure reader and the new audit.
- Total sleep's absolute limits of agreement are wider, not narrower, than deep sleep's. High correlation is not accuracy.
- The deep-sleep decomposition is proportional-duration accounting, not evidence of an exact epoch-by-epoch reassignment.
- Schyvens collected data in April 2023–August 2024 and participants wore two to four devices. The article no longer claims laboratories cannot compare simultaneous wearables.
- Charge 5 laboratory offsets and Charge 6 home differences are descriptive comparators, not a formal test of a fixed error-free prediction. Lab estimate uncertainty is not included in the home intervals.
- Recovery–RHR correlation is overlap, not proof of equivalence. Next-day Fitbit RHR is not an independent reference for Fitbit sleep staging.

## Algorithm-dating discipline

The primary-source timeline separates events before the wear windows, between them, within the spring window and after both. WHOOP's July 2026 HR release is explicitly excluded as an explanation of October–May differences. Fitbit's March 2026 sleep update is identified as Public Preview, not presumed universal. WHOOP's 2025 staging update was already described by staff in May; a December recap or a later article update is not its release date.

WHOOP's current consumer description says midnight reset; its developer API documents physiological cycles. These cannot resolve this export's historical dating rule. The actual cycle IDs, timestamp mapping and score completeness are still required.

## Source retrieval

Perplexity reasoning was used to locate candidate releases, then primary pages were inspected directly. Several synthesis claims were corrected against those pages, notably the date of muscular-load introduction and Fitbit's Readiness redesign. The publisher page for Schyvens extracted only navigation; PMC timed out/challenged the browser; Europe PMC's fullTextXML endpoint returned the paper, including Tables 3, 10 and 11. The article cites the canonical PMC source; the retrieval mirror is also in the ledger.

## Unresolved

- Original wide-table extraction SQL and HR provenance/coverage.
- WHOOP cycle/calendar mapping and timestamp-aligned sessions.
- Historical max/resting HR and raw HR needed for actual TRIMP.
- WHOOP 4.0-specific rollout confirmation for 2026 entries where eligibility is not stated.
- Fitbit Public Preview participation and exact per-account algorithm versions.
- No reference PSG/chest-strap validation and no causal estimate of algorithm-update effects.

These are limitations of the analysis, not unfinished software deployment. No publication was requested or performed.
