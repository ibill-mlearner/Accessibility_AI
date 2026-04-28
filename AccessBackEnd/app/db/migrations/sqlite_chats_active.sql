-- Migration intent:
-- Add `chats.active` for legacy SQLite files so chat lifecycle state can be
-- toggled without deleting conversation history.
ALTER TABLE chats ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1;
