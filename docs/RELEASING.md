# Preparing a presentation or release

The repository is being prepared for publication on GitHub with a Zenodo
archive. Decided by the author on 3 October 2026: raw data stay public, code
under MIT, text, data and figures under CC BY 4.0, English-only article, author
Emilien Waltz without institutional affiliation. Publishing, tagging and
archiving still require the author's explicit approval of the exact version.

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

| Decision | Status |
|---|---|
| Author list | Emilien Waltz; whether a contributor is credited as co-author or acknowledged is undecided |
| Affiliation | None (independent researcher) |
| Licence | Decided: MIT for code, CC BY 4.0 for text, data and figures |
| Data disclosure | Decided: raw databases, coded CSV and diagnostics with excerpts remain public and documented |
| Human-validation account | Partly declared, see [coding provenance](CODING_PROVENANCE.md); open points listed there |
| Scientific declarations | Chronology, conflicts/funding and ethics statement to be provided by the author |
| Venue and release action | GitHub release archived on Zenodo; each push, tag and deposit needs explicit approval |

The missing facts do not block local tests, reproduction, manuscript revision or
export preparation. They prevent an honest claim that external publication or
independent human validation is already settled. See the manuscript declarations
and [experiment plan](../paper/EXPERIMENT_PLAN.md).

## Citation status

There is no DOI for SNAP yet. [CITATION.cff](../CITATION.cff) carries the
decided author and licences; the version, release date and DOI are added only
when a release is approved and archived. `paper/references.bib` contains the
verified *external* literature cited by the manuscript, not a citation for this
project.
