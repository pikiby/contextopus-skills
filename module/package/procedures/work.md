---
operations:
  - skill_catalog.source_list
  - skill_catalog.discover
  - skill_catalog.inspect
  - skill_catalog.read
  - skill_catalog.source_read
  - skill_catalog.file_read
  - skill_catalog.search
  - skill_catalog.related
  - skill_catalog.compare
  - skill_catalog.save
  - skill_catalog.refresh
  - skill_catalog.reconcile
---
# Find, inspect and organize skills

1. Determine whether the user wants retrieval, catalog maintenance or comparison. Retrieve existing cards first. Assess shared search diagnostics and filter scope; semantic proximity is a candidate, not a proven duplicate.
2. For a known installation, read its card and the current source instruction through source_read. For a new installation, discover an explicitly registered root and inspect the selected relative SKILL.md location. Read the package files needed for the card requirements below. Use file_read at the returned package_revision for an existing card. Before a new card exists, use the host's authorized read-only file reader for the exact discovered package paths; do not create a placeholder card just to unlock file_read. Reinspect before saving and verify that the reviewed package has not changed. A catalog card is a description, not the executable instruction. Reading an instruction for analysis does not authorize its commands.
3. Before authoring a card, inspect related catalog entries. Compare actual instructions, triggers, tools, dependencies and limits. Distinguish identical packages, identical instructions with different supporting files, functional overlap, complementary skills and unrelated skills. Do not merge by name or vector distance. No similarity threshold establishes safe deletion.
4. Save an accurate short description and a Markdown body meeting every requirement in "Card contents" below. A frontmatter description copied into a generic wrapper is not a complete card. Record the compared card links and actual package revisions with the conclusion. Use links such as [[other-card-id]]. Preserve relevant existing descriptions and use the current card revision. The reviewed_revision must be the package_revision actually inspected. Save does not move, install, synchronize, modify or execute the source skill.
5. Verify the save/index result. The owner reconciliation for pending indexing is skill_catalog.reconcile. After installed skill files change, use refresh: it updates observations and marks descriptions requiring review without rewriting the agent's conclusions. Re-read affected instructions before updating descriptions. A prior comparison is applicable only to its recorded revisions; source_read/compare checks current bytes.


## Card contents

Keep the short description useful for semantic selection. Put the following concrete information in the card body, where a person reading the card can see it without joining source metadata:

- **Purpose and use:** what the skill does, when to choose it, what inputs it needs and what result it produces. State its material limits and distinguish inspection, preparation and execution.
- **Location and invocation:** save derives the absolute `SKILL.md` path, containing directory and inventory. The agent records the verified invocation and explains the registered source/client when relevant; do not guess paths from a name.
- **Package files:** supply a concise content-based purpose for every path returned by inspect.files, including instructions, scripts, references, templates, configuration and assets. Save renders those paths and purposes. Read scripts as source, never execute them for cataloging. Filenames and hashes alone do not establish purpose. For binary assets, use a suitable reader or evidence from the instruction/configuration that references them; state that evidence. Mark unreadable or unresolved meanings explicitly rather than inventing them or claiming a complete review.
- **Tools and dependencies:** name the tools, MCP services, runtimes, libraries, credentials by name only, and external instructions actually required by this skill. Distinguish required and conditional dependencies. List references outside the package separately, with their resolved locations when verified; do not present them as bundled files. Reading source does not prove a service is connected or a script works.
- **Aliases and relationships:** for a verified alias, link the original catalog card using an Obsidian link, identify the original invocation and source instruction path, and explain the inspected forwarding/configuration evidence. Populate the corresponding alias metadata as specified in skill_catalog/catalog. Similar functionality or a similar name is not an alias. If the target cannot be verified within scope, report the unresolved relationship instead of inventing one.
- **Review boundaries:** retain the inspected package revision and any comparison evidence. Describe specific missing evidence or compatibility limits; do not substitute boilerplate disclaimers for the information above. Do not copy the complete source instruction into the card.

Supply file_purposes as a mapping of every relative path from inspect.files to the purpose
established by reading. Save verifies that no file is omitted or invented, derives absolute
paths and file hashes, and adds the Installed package section itself. Its reserved
`<!-- contextopus-package -->` footer is regenerated on save; keep authored analysis above it.
Do not duplicate paths and inventory manually in the body. Meaning, applicability, file
purposes, dependencies and alias evidence remain the agent's analysis. The code cannot
verify that the agent actually read a file. Check the returned card and index result.
Cataloging does not authorize source edits, installation, synchronization or execution.

One card describes one installation, identified by registered source and relative SKILL.md location. Different copies remain distinct until the agent establishes their relationship. A move outside the original location appears as a missing old installation and a new candidate; do not guess identity from a name.

This module reads installed skill packages and writes only its own catalog. For an explicit
request to create, register or change a skill in an environment, the agent chooses and reads
that environment's applicable skills and uses its native tools. Cataloging is not native
skill creation. This module provides no synchronization, adaptation or source deletion
commands. No timer or automatic background inventory is started. Discovery reports
inaccessible, missing, symbolic-link or oversized roots as errors rather than empty success.
