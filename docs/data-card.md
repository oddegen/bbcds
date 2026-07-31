# BBCDS Data Card: Baseline V1 Research Snapshot

## Dataset Details

- Dataset: BBCDS preparation of `deepghs/nsfw_detect`.
- Version: unversioned upstream snapshot used on 2026-07-31.
- Prepared-data owner: BBCDS project; upstream distribution owner: `deepghs`.
- Review status: approved for `baseline-v1` research use only; this is not a
  production-calibration or video-performance approval.
- Manifest hash:
  `46c18a29ac0436b6b7dfe72e9919cc6ad49fd29309bbe5bc3851b2ad3e122e95`.
- Access location: access-controlled storage outside the repository.

## Motivation And Uses

The snapshot supports research training and image-level validation for the BBCDS
four-class visual taxonomy: `Safe`, `Suggestive`, `Explicit`, and
`Explicit Illustration`.

Permitted uses are research baseline training, protected validation, and
preparation for later model-artifact compatibility work. It must not be used for
public redistribution, universal safety claims, unrelated classifiers, or claims
about gore, violence, self-harm, drugs, hate, text, or audio.

## Composition

- Modality: still images.
- Scanned records: 28,000.
- Accepted records: 27,803.
- Source groups: 27,395.
- Splits: 22,242 train; 2,781 validation; 2,780 test; no separate holdout.
- Labels: 11,134 Safe; 5,543 Suggestive; 5,559 Explicit; 5,567 Explicit Illustration.
- Deduplication and exclusions: 191 exact duplicates, 367 accepted near-duplicate
  clusters, 8 conflicting-cluster records excluded, 0 corrupt records, and 0
  policy-list exclusions.

| Split      |  Safe | Suggestive | Explicit | Explicit Illustration | Source groups |
| ---------- | ----: | ---------: | -------: | --------------------: | ------------: |
| Train      | 8,907 |      4,435 |    4,447 |                 4,453 |        21,849 |
| Validation | 1,114 |        554 |      556 |                   557 |         2,773 |
| Test       | 1,113 |        554 |      556 |                   557 |         2,773 |

No media paths, filenames, URLs, thumbnails, pixels, or record-level class
probabilities are included in this public card.

## Collection And Provenance

- Upstream collection: `deepghs/nsfw_detect`.
- Collection date range: not documented in retained evidence.
- License: upstream repository-level MIT declaration; underlying-media rights,
  provenance, and consent are not verified.
- Permitted use: BBCDS research baseline only; no commercial-clearance claim.
- Removal/takedown process: remove identified content by protected SHA-256 exclusion,
  issue a new manifest hash, repeat the review, and retrain affected models.
- Source domains and excluded-source identities: not published and incompletely
  documented upstream.

## Preparation And Labeling

- Supported images were decoded with Pillow and hashed with SHA-256 and a perceptual hash.
- Exact duplicates were removed; perceptual near-duplicates were grouped; groups with
  conflicting labels were excluded.
- Upstream folders were mapped to the canonical taxonomy: neutral/drawing to Safe,
  sexy to Suggestive, porn to Explicit, and hentai to Explicit Illustration.
- Upstream annotator qualifications, annotator count, adjudication, and safety
  procedures were not documented in the retained evidence.
- BBCDS did not perform an independent record-level re-annotation. Ambiguous records
  detected through conflicting exact or near-duplicate groups were excluded.
- Reviewer approval: `project-owner`, limited to research-baseline use.

## Split Policy And Quality Controls

- Deterministic seed: `20260731`; target ratios: 80% train, 10% validation, 10% test.
- Exact and near-duplicate groups were assigned as a unit.
- Manifest validation requires every source group to occur in exactly one split.
- Approval finalization recomputes split, label, per-label/per-split, and source-group
  aggregates from the protected manifest and checks them against the audit and report.
- Any manifest-hash, count, canonical-label, or split-isolation mismatch blocks approval.

## Bias, Risks, And Limitations

- Geographic, demographic, age, source-domain, and collection biases are not measured.
- Folder-derived labels may be ambiguous and do not substitute for a documented
  multi-reviewer annotation protocol.
- The Safe class combines neutral and drawing sources and is twice the size of each
  other class; training used class weights to mitigate this imbalance.
- Synthetic and illustration coverage is limited to the upstream snapshot.
- Image-level evidence cannot establish behavior on compression, motion, transitions,
  temporal context, frame sampling, or whole-video aggregation.
- Provenance and rights gaps make this snapshot unsuitable for commercial-clearance claims.

## Distribution, Maintenance, And Contacts

- Protected media, manifests, source linkage, and evaluation evidence remain in
  access-controlled storage outside Git.
- Public material is limited to aggregates, opaque hashes, and approved limitations.
- Every dataset change requires a new manifest hash, isolation checks, aggregate
  distributions, provenance review, model card, validation report, and retraining decision.
- Dataset owner, safety reviewer, release approver, and takedown contact:
  BBCDS project owner.
