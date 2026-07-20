# Feature Spec: UpToCode 1.1 Beta Access Control

Status: deferred; specification only. D005 prohibits implementation in 1.0.

## Purpose

Replace manually provisioned key hashes with an operator-controlled access lifecycle when
private-beta scale and support load justify persistent state.

## Scope

### In scope for a separately approved 1.1 implementation

- Authenticated operator issuance, rotation, revocation, expiry, and audit history.
- Firestore-backed access records with explicit retention and deletion rules.
- Transaction-safe quotas designed to avoid single-document write hot spots.
- A minimal operator CLI; no public admin interface by default.
- Migration from the current secret-backed hash allowlist without exposing raw keys.

### Out of scope

- Storing submitted source, prompts, reports, or model payloads.
- Public access-request collection until a separate PII/privacy decision approves it.
- Weakening the existing in-memory rate limit, hosted-judgment gate, or safe logging.

## Risks and safety checks

- Contact data and access records introduce the product's first persistent PII surface.
- Firestore security rules, indexes, backup/restore, regional placement, retention,
  deletion, and incident response require review before provisioning.
- Raw keys are shown once, stored only by the recipient, and never logged or persisted.

## Acceptance criteria for future implementation

- [ ] Threat model and privacy/retention decision are approved.
- [ ] Issuance, rotation, revocation, expiry, and concurrency tests pass.
- [ ] Quotas remain correct under concurrent requests without document hot spots.
- [ ] Logs and stored records contain no raw key or submitted code.
- [ ] Rollback to the secret-backed allowlist is documented and rehearsed.
