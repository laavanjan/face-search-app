## What changes

## Governance checklist (docs/governance/change-management.md)

- [ ] Change class: minor / material / major
- [ ] Touches model, thresholds, AWS usage, legal basis, retention, access control or deployment? → change record added in `docs/changes/` with the re-evaluation result
- [ ] Re-indexing needed (model or embedding change)? Plan described in the change record
- [ ] Risk register / risk assessment updated if a risk changed
- [ ] Privacy docs updated if data collected, retained or shared changed
- [ ] Tests cover the new behaviour (`cd backend && pytest`)
