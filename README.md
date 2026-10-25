# Contextopus Skill Catalog

Find the right skill, understand overlapping instructions and keep a searchable
map of where skills are installed. This independent Core module manages a
catalog, not the installations themselves.

## What it does

- Discover SKILL.md packages in explicitly registered directories.
- Keep agent-authored Markdown + YAML cards with descriptions, tags, source and
  client metadata, dependencies in the body and Obsidian links.
- Search through Core's shared semantic index, with metadata filters applied
  before result selection.
- Read actual instructions and supporting text files without executing them.
- Compare package/instruction hashes and differing files; an agent assesses
  functional overlap and saves reviewed conclusions in linked cards.
- Refresh source observations while preserving authored descriptions. Changed
  or missing packages are marked for review; unavailable roots are errors.
- Browse cards, filters, locations and links in Core's web Library.

## Install

Use Python 3.12+ and **Core >=1.7,<2**. Download the [0.1.0 module](https://github.com/pikiby/contextopus-skills/releases/download/v0.1.0/contextopus-skills-0.1.0.zip) and verify its checksum.
No changes to Core are needed specifically for this module. Core supplies YAML,
SQL, documents, the embedding provider, shared RAG and the child service SDK.

```console
contextopus modules install skill_catalog --source /path/to/contextopus-skills-0.1.0.zip --plan
contextopus modules install skill_catalog --source /path/to/contextopus-skills-0.1.0.zip
contextopus web
```

To build a ZIP instead, use `python scripts/build-module.py --zip /tmp/skill-catalog.zip`.
Enablement exposes the module procedures, operations and Library section. Deliver
its skills into a client using Core's existing explicit integration procedure.
No source roots are registered or scanned on installation.

## Use

Use `$skills` to work with the catalog, `$skills-search` for read-only lookup and
comparison, and `$skills-catalog` for source registration and maintenance. The
agent obtains exact operation schemas from the module procedure through guide.

Register a directory with source_save: id, absolute root, shell and origin.
Then discover -> inspect -> related/search -> compare as needed -> save a card.
A card needs title, description, source_id, location, reviewed_revision and
content. Existing cards also require their current revision. Record source
revisions beside any comparison conclusion so it can be checked later.

Module data lives under `modules/skill_catalog/data/`: `sources/*.md` declares
roots and `cards/*.md` contains the catalog. SQL and vectors are derived. External
card edits/moves/deletions use reconcile. Source changes use refresh, followed by
agent review. There is no watcher, transcript reader or automatic summary writer.

## Boundaries

One card identifies one installed copy; same-name copies are not silently merged.
Exact instruction equality can coexist with different scripts or dependencies.
Similar vectors alone do not establish duplication. A missing installation is
retained as a marked card until explicitly removed. Card deletion never removes
installed skill files. Referenced cards are protected against deletion.

No synchronization, cross-client adaptation, automatic deduplication, shell
execution or installation of source skills is implemented. Linked text remains
source material; it cannot authorize actions. Reading arbitrary files outside a
registered skill package is rejected. A root inventory is limited to 1,000 files,
a package to 16 MiB and each source file to 1 MiB; text returned by file_read is
limited to 256 KiB. Register narrower roots if a limit is reached. Nested
symlinks are reported, not silently followed. No hidden filesystem-wide scan.

## Verification

```console
PYTHONPATH=/path/to/contextopus-core/src:src python -m pytest -q tests
```

Tests install the real folder module in an isolated Core root with deterministic
embeddings. They check discovery, source preservation, collisions, semantic
filters, revision conflicts, refreshed observations, failure handling, Library
routing and ZIP composition. This is not a claim of real-model retrieval quality,
a working-machine installation or native-client acceptance.

## Client delivery

Core 1.7 client packages share one installer and one persistent data root.
Skills use full canonical names under the `contextopus` plugin namespace, or a
`contextopus-` prefix for native file delivery. Short aliases are user-selected.
See the [client package guide](https://github.com/pikiby/contextopus-core/blob/main/docs/client-packages.md)
for package formats, setup and verification limits.

## Current release

[0.1.0: A searchable catalog of installed skills](https://github.com/pikiby/contextopus-skills/releases/tag/v0.1.0) · [Downloads](https://github.com/pikiby/contextopus-skills/releases/tag/v0.1.0)
