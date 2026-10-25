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
5. Verify the save/index result. A pending index is not a lost file: retry reconcile after resolving the cause. After installed skill files change, use refresh: it updates observations and marks descriptions requiring review without rewriting the agent's conclusions. Re-read affected instructions before updating descriptions. A prior comparison is applicable only to its recorded revisions; source_read/compare checks current bytes.


## Card contents

Keep the short description useful for semantic selection. Put the following concrete information in the card body, where a person reading the card can see it without joining source metadata:

- **Purpose and use:** what the skill does, when to choose it, what inputs it needs and what result it produces. State its material limits and distinguish inspection, preparation and execution.
- **Location and invocation:** the verified absolute path to `SKILL.md`, its containing directory, the registered source, client and installed invocation name. Derive paths from the registered root and discovered location; do not guess paths from the skill name. Make file paths clickable Markdown links.
- **Package files:** list every file returned by the inspected package inventory, including instructions, scripts, references, templates, configuration and assets. For each file give its relative path, a link to the actual file and a concise purpose based on reading its contents. Use a table or grouped lists; a file count or directory names alone are insufficient. Read scripts as source, never execute them for cataloging. Filenames, hashes and extracted headings alone do not establish a file's purpose. For binary assets, use a suitable reader or evidence from the instruction/configuration that references them; say which evidence establishes their role. Explicitly mark anything unreadable or unresolved rather than inventing its purpose or claiming a complete review.
- **Tools and dependencies:** name the tools, MCP services, runtimes, libraries, credentials by name only, and external instructions actually required by this skill. Distinguish required and conditional dependencies. List references outside the package separately, with their resolved locations when verified; do not present them as bundled files. Reading source does not prove a service is connected or a script works.
- **Aliases and relationships:** for a verified alias, link the original catalog card using an Obsidian link, identify the original invocation and source instruction path, and explain the inspected forwarding/configuration evidence. Populate the corresponding alias metadata as specified in skill_catalog/catalog. Similar functionality or a similar name is not an alias. If the target cannot be verified within scope, report the unresolved relationship instead of inventing one.
- **Review boundaries:** retain the inspected package revision and any comparison evidence. Describe specific missing evidence or compatibility limits; do not substitute boilerplate disclaimers for the information above. Do not copy the complete source instruction into the card.

Before saving, compare the file list with the inspected inventory, check absolute paths and alias targets, and confirm that each purpose and dependency has supporting content. After saving, read back the card to check these fields and its links, then verify indexing. Cataloging does not authorize source edits, installation, synchronization or execution.

One card describes one installation, identified by registered source and relative SKILL.md location. Different copies remain distinct until the agent establishes their relationship. A move outside the original location appears as a missing old installation and a new candidate; do not guess identity from a name. Ordinary Obsidian links do not adopt instructions. Follow explicit required_links before dependent work through the authorized owning reader.

This module is a read-only reader of installed skill packages and a writer of its own catalog. It provides no synchronization, adaptation or source deletion commands. Those remain separately authorized agent tasks. No timer or automatic background inventory is started. Discovery is bounded and reports inaccessible, missing, symbolic-link or oversized roots as errors rather than an empty success.
