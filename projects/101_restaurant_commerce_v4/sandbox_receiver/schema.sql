CREATE TABLE IF NOT EXISTS receipts (
  id TEXT PRIMARY KEY,
  event_json TEXT NOT NULL,
  received_at INTEGER NOT NULL,
  acked_at INTEGER
);
CREATE INDEX IF NOT EXISTS receipts_pending ON receipts(acked_at, received_at, id);
