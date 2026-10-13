# Stakeholder impact assessment

| | |
|---|---|
| System | Face Search (1:N face identification over a private photo collection) |
| Assessor | System Owner (@laavanjan) |
| Date | 2026-10-14 |
| Next review | 2027-01-14, or on any trigger in [change-management.md](change-management.md) |

| Stakeholder | How they are affected | Benefit | Potential harm | Voice / recourse | Mitigation in place |
|---|---|---|---|---|---|
| **People shown in indexed photos** (incl. non-users, bystanders, children) | Their face is converted to a biometric embedding and becomes findable | Can find their own photos in a shared library | Indexed without knowing; found by someone they did not want to be found by; misidentified | `/appeal` without an account; objection immediately excludes the photo from search | Consent confirmation at upload; reviewer approves indexing; retention TTL; deletion on request |
| **Person in a search reference photo** | Their face is compared against the whole library | Finds photos of themselves | Search run on them without consent | Appeal; audit log shows who searched | Consent confirmation for searches; reference photo kept only during review |
| **Search result subjects** | Their photo may be released to the requester as a match | Correct match | False match disclosed to a third party | "Report incorrect match" next to every result | Results released only after reviewer verification; minimum similarity floor |
| **Operators** (uploaders/searchers) | Use the tool | Saves manual sorting of photos | Rely on a wrong match; held responsible for unlawful use | Can ask the reviewer to re-examine | AI disclosure, "not an identification" notice, consent prompts |
| **Human Reviewers** | Make the final call on matches | Clear queue and evidence | Automation bias; workload; exposure to others' photos | Can escalate to System Owner | Training requirement; side-by-side evidence; reason required for every decision |
| **System Owner / organisation deploying it** | Legal and reputational accountability | - | Regulatory breach (biometric law), data breach | - | This governance pack; RBAC; audit log; stop switch |
| **Third-party processors** (AWS Rekognition/S3 when enabled; Qdrant Cloud if used) | Receive or store images/vectors | - | Become a breach surface; cross-border transfer | Contractual terms | Off by default; [transfer assessment](../privacy/cross-border-transfer-assessment.md) required before enabling |
| **Model provider** (InsightFace) | Licence terms govern use of weights | - | Licence breach if used commercially | - | [Training-data and licence record](../privacy/training-data.md) |
| **Society / groups under-represented in model training data** | Different error rates across groups | - | Disparate false matches | Appeals; risk register R-03 | Human review of every match; fairness evaluation required before threshold changes |

## Conclusion

Benefits are limited and personal (organising one's own photos); harms fall mostly on people who are
not users. The system is therefore restricted to consented private collections, operates fail-closed
behind human review, and offers recourse to non-users. See the ranked impacts in
[risk-assessment.md §5](../risk/risk-assessment.md).
