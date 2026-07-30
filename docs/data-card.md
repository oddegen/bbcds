# BBCDS Data Card

No protected dataset is bundled in this repository. This file is the public
template for the protected data card used by model training and validation.

## Dataset Details

- Dataset name:
- Version:
- Owner:
- Review status:
- Manifest hash:
- Access location:

## Motivation

The dataset supports browser-only visual moderation for the BBCDS four-class
taxonomy:

- `Safe`
- `Suggestive`
- `Explicit`
- `Explicit Illustration`

It must not be used to claim coverage for unrelated safety categories such as
gore, general violence, self-harm, drugs, hate symbols, unsafe text, or audio.

## Composition

Complete this section inside the protected process:

- Total record count:
- Source-group count:
- Split counts:
- Label distribution:
- Modality:
- Source domains:
- Excluded record count:
- Sensitive-content handling:

Public documentation must use aggregate counts, opaque identifiers, and hashes
only.

## Collection And Provenance

Complete this section inside the protected process:

- Dataset owner:
- Collection name:
- Collection date range:
- License and permitted use:
- Consent or rights review:
- Removal and takedown process:
- Excluded sources:

Do not commit source media, filenames, URLs, thumbnails, frame pixels, or class
probabilities.

## Preprocessing And Labeling

Document the annotation protocol before training:

- Preprocessing steps:
- Label definitions:
- Annotator qualifications:
- Minimum annotator count:
- Adjudication process:
- Reviewer approval:
- Annotator safety procedure:
- Ambiguous-content handling:
- Quality-control checks:

Records with unresolved label quality or provenance concerns must be excluded
from model training and validation.

## Split Policy

Splits must be grouped by source. Frames, clips, or near-duplicates from the same
source must not appear in more than one split.

Required split documentation:

- Train, validation, test, and holdout counts.
- Per-label distribution by split.
- Source-group isolation check.
- Exclusion counts and reasons.
- Dataset manifest hash.

Machine-readable dataset metadata must conform to
`model/dataset-manifest.schema.json`.

## Uses

Intended use:

- Training and validating the accepted four-class visual taxonomy.
- Producing aggregate evidence for model approval.
- Measuring known limitations before release.

Prohibited use:

- Public redistribution of protected media or sensitive linkage metadata.
- Training unrelated safety classifiers without a new review.
- Benchmarking claims outside the documented taxonomy.
- Any workflow that exposes source identity or content samples in public commits.

## Distribution And Access

Protected media, manifests with sensitive linkage, annotation exports, and
evaluation outputs must live outside the public repository in an access-controlled
location. Access must be limited to approved reviewers and operators.

Public commits may contain only schemas, empty templates, aggregate metrics,
opaque hashes, and approved limitations.

## Bias, Risks, And Limitations

Completed data cards must document:

- Known collection bias.
- Geographic, demographic, style, and source-domain gaps.
- Label ambiguity.
- Synthetic or illustration coverage.
- Differences between image-level evaluation and video-level product behavior.
- Any class with insufficient validation support.

## Maintenance

Every dataset update requires:

- A new manifest identifier and hash.
- Re-run source-group isolation checks.
- Updated aggregate distributions.
- Review of provenance and license changes.
- Updated model card and validation report when a model is trained from the data.

## Contacts

- Dataset owner:
- Safety reviewer:
- Release approver:
- Takedown contact:
