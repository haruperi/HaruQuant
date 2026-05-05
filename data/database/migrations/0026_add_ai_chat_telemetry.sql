-- Phase 12: Observability, Latency, Cost, and Scale
-- Instrument ai_chat_messages with technical telemetry

ALTER TABLE ai_chat_messages ADD COLUMN prompt_tokens INTEGER;
ALTER TABLE ai_chat_messages ADD COLUMN completion_tokens INTEGER;
ALTER TABLE ai_chat_messages ADD COLUMN total_tokens INTEGER;
ALTER TABLE ai_chat_messages ADD COLUMN cost REAL;
ALTER TABLE ai_chat_messages ADD COLUMN latency_ms INTEGER;
