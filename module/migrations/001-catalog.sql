CREATE TABLE "{{module}}::metadata"(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE "{{module}}::cards"(id TEXT PRIMARY KEY, document TEXT NOT NULL, indexed_revision TEXT, index_error TEXT);
