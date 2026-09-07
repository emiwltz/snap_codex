# Preparing a presentation or release

The working repository is ready for structured local review. A public release,
licence and scientific submission have not been approved. The author name,
affiliation and licence are explicitly undecided. No placeholder identity is
presented as a real author and no licence has been chosen on the owner's behalf.

## Prepare the local bundle

After the README installation and local checks:

```bash
.venv/bin/python scripts/export_presentation.py --output-dir artifacts/exports/review-01
```

This command creates a ZIP and a SHA-256 manifest locally, in a new directory. It
does not contact a hosting service, push Git or publish the manuscript. Contents
come from [an explicit file list](presentation-files.txt); adding an unrelated
file to the working tree does not silently add it to the export.

The export checks paths, symlinks, known credential patterns, personal absolute
paths, included Markdown links and normalized exact 160-character prefixes from
reference responses and judge justifications. JSON strings are decoded and PDF
text extracted. Output reports identify paths and issue classes without printing
matched text or credentials. PNG figures need visual review; a substring scan is
not semantic detection or approval of copyright, privacy or data rights.

Raw databases, coded CSV, the diagnostic containing excerpts, archival prose not
reviewed for response quotations, original private provenance records, caches,
runtime and Git history are omitted. The [data guide](DATA.md) explains why this
is a presentation bundle with tests and aggregates, not full raw-data replication.
The source references remain in the working repository.

Do not use `git archive` or push the working history as a substitute: tracked raw
data remains tracked despite ignore rules. Review `EXPORT_NOTICE.md`, the archive
inventory and the PDF before using the bundle outside the local review.

## Decisions remaining before external release

| Decision | Required fact or authorization |
|---|---|
| Author name and affiliation | Owner's chosen public attribution; both undecided |
| Licence | Owner's choice and appropriate rights for code, text, inputs and outputs |
| Data disclosure | Whether and under what terms raw responses/coding may be distributed; review excerpts first |
| Human-validation account | Coder identity/role, independent work, blinding, instructions and adjudication conditions |
| Scientific declarations | Real chronology, conflicts/funding, applicable ethical review or rationale, rights statements |
| Venue and release action | Target if any, final review and explicit permission to publish or submit |

The missing facts do not block local tests, reproduction, manuscript revision or
export preparation. They prevent an honest claim that external publication or
independent human validation is already settled. See the manuscript declarations
and [experiment plan](../paper/EXPERIMENT_PLAN.md).

## Citation status

There is no DOI for SNAP and no settled author metadata. Cite the actual working
version and commit in an internal review; do not invent a BibTeX author, DOI,
licence or affiliation. `paper/references.bib` contains the verified *external*
literature cited by the manuscript, not an official citation for this project.
