Run `make check-all`. If anything is red, fix it before proceeding.
Then produce, in order:
1. Execution report: what changed and why; commands run with outcomes;
   red→green history; any destructive action that was confirmed.
2. Draft CHANGELOG entry (Keep a Changelog format) for this sprint. The
   draft rides the next gate bump commit — it is never committed
   mid-phase.
3. Draft PR description; if any public symbol changed, include the
   design-review note.
4. New decisions for the D-ledger and any new IOUs.
Do not commit or push until the report is approved.
