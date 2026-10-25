---
operations:
  - skill_catalog.source_list
  - skill_catalog.source_save
  - skill_catalog.discover
  - skill_catalog.inspect
  - skill_catalog.read
  - skill_catalog.save
  - skill_catalog.refresh
  - skill_catalog.reconcile
  - skill_catalog.delete
  - skill_catalog.status
---
# Maintain the catalog

Register only explicit authorized absolute directories using source_save, with a source ID, client/shell and origin (user, repository, plugin or another truthful label). Registration saves a small source Markdown file and does not scan it. Root paths are immutable and may not overlap. No entire-home scan or guessed client directory is implied. Symlink targets can be registered explicitly; nested symlinks are not followed.

Discover reads SKILL.md packages without writing cards. Read skill_catalog/work before creating or revising descriptions and apply its Card contents requirements: verified absolute locations, complete package inventory with content-based file purposes, applicability, tools/dependencies and verified alias links. A source registration or discovered file list alone is not a finished catalog card. refresh updates observations for existing cards and identifies missing installations only after successful complete source inventories. Missing roots, access errors and inventory limits abort that update. Missing skills leave their catalog card available for review; refresh never deletes it or transfers a guessed identity to a new path.

External edits, moves or deletion of catalog Markdown require reconcile. It applies Core's common file plan to derived SQL and RAG; it does not write installed skills. delete removes only one explicitly selected card at its current revision. First examine incoming card links and resolve them under the request; the operation rejects incoming links rather than silently breaking them. Deleting a catalog card is not uninstalling its skill. Do not delete anything solely because a scan or similarity search suggests a duplicate.

Record original_name and invocation_name when verified. Use relationship=original, native_alias, forwarder or renamed_copy. Native aliases and forwarders require alias_target as a wikilink and alias_evidence describing the inspected client configuration or forwarding file. Similar text is not evidence of an alias. Keep edited copies distinct. The catalog records relationships; it does not install, rename or synchronize source skills.
