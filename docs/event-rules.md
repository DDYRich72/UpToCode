# OpenAI Build Week Rules Checklist

This checklist operationalizes the official rules encoded in
`tasks/completion-plan-v2.md` §2. The rules were fetched on 2026-07-19 from
<https://openai.devpost.com/rules>. “Operator” items require an explicit human action;
Codex must stop before performing them.

| Requirement | Evidence or action | Owner | Status |
|---|---|---|---|
| Submit between 2026-07-13 09:00 PT and **2026-07-21 17:00 PT** | Repository history begins during the submission period; submit with buffer and record the final URL/timestamp in `PROGRESS.md`. | Operator ⛔ | Pending submission |
| Demo is **under three minutes**, has audio, and explains both the product and how Codex and GPT-5.6 were used | Timed script and recording checklist in `docs/demo-script.md`; final duration checked before upload. | Codex: script; operator ⛔: record/upload | Script ready; recording pending |
| Demo is publicly available on YouTube | Upload only after operator approval; add the public URL to the Devpost entry. | Operator ⛔ | Pending |
| Demo contains no third-party trademarks or copyrighted material | Capture only ArchAgent-owned UI, checked-in fixtures, terminal output, and narration; no third-party logos, marks, or music. | Codex: guardrails; operator ⛔: final review | Guardrails ready |
| Repository is public with licensing, or private and shared with the two judging accounts | Keep the MIT-licensed repo private; share with `testing@devpost.com` and `build-week-event@openai.com`. | Operator ⛔ | Pending sharing |
| README describes collaboration with Codex throughout development | `README.md` “Built with Codex and GPT-5.6”; planning, decisions, progress, and validation artifacts in-repo. | Codex | Complete |
| Submission includes the Codex Session ID for the core-functionality task | Capture from the Codex UI and store only in private submission notes, never in the repository. | Operator ⛔ | Captured outside repository; form entry pending |
| Judges can access a functioning demo, website, or test build | Exact private-clone, install, CLI, review, FIXPLAN, acceptance, and MCP instructions in `README.md`. | Codex; operator ⛔ grants repo access | Instructions complete |
| Entry is built with both Codex and GPT-5.6 | README, demo script, and Devpost draft describe Codex collaboration and the opt-in GPT-5.6 Structured Outputs judgment tier. | Codex | Complete |
| Entry is original, solely owned, non-malicious, and respects IP | MIT license; original project files; dependency audits and compliance gate; no third-party demo assets. Final ownership attestation remains an operator submission action. | Codex: evidence; operator ⛔: attest | Evidence ready |

## Submission-ready evidence

- Sanitized product captures: `docs/submission-evidence/`.
- Cross-platform test counts, coverage, dependency checks, and environment versions:
  `tasks/validation-report.md`.
- Current delivery state and self-scan disposition: `PROGRESS.md`.
- Submission copy: `docs/devpost-draft.md`.
- Final operator-only fields kept outside the repository: Codex Session ID, YouTube URL,
  optional hosted credentials, and submission URL until submitted.
