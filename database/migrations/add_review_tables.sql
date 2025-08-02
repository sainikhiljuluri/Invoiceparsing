-- Human Review System Database Schema
-- This migration adds tables for managing human review of product matches

-- Human review queue table
CREATE TABLE IF NOT EXISTS human_review_queue (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(255) NOT NULL,
    invoice_item_id VARCHAR(255),
    product_info JSONB NOT NULL,
    priority INTEGER DEFAULT 2, -- 1: High (low confidence), 2: Medium, 3: Low
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, skipped
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    review_decision JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Product mappings for learning from human decisions
CREATE TABLE IF NOT EXISTS product_mappings (
    id SERIAL PRIMARY KEY,
    original_name VARCHAR(500) NOT NULL,
    normalized_name VARCHAR(500),
    mapped_product_id VARCHAR(255) NOT NULL,
    vendor_key VARCHAR(100) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    mapping_source VARCHAR(50) DEFAULT 'human', -- 'human', 'ai', 'rule'
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(original_name, vendor_key)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON human_review_queue(status);
CREATE INDEX IF NOT EXISTS idx_review_queue_priority ON human_review_queue(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_review_queue_invoice ON human_review_queue(invoice_id);
CREATE INDEX IF NOT EXISTS idx_product_mappings_vendor ON product_mappings(vendor_key);
CREATE INDEX IF NOT EXISTS idx_product_mappings_original ON product_mappings(original_name);
CREATE INDEX IF NOT EXISTS idx_product_mappings_active ON product_mappings(is_active);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_review_queue_updated_at 
    BEFORE UPDATE ON human_review_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional)
-- INSERT INTO human_review_queue (invoice_id, product_info, priority) VALUES 
-- ('test-invoice-1', '{"product_name": "Test Product", "confidence": 0.65}', 1);

COMMENT ON TABLE human_review_queue IS 'Queue for items requiring human review due to low confidence matches';
COMMENT ON TABLE product_mappings IS 'Learned mappings from human review decisions to improve future matching';
COMMENT ON COLUMN human_review_queue.priority IS '1: High priority (low confidence), 2: Medium, 3: Low';
COMMENT ON COLUMN product_mappings.mapping_source IS 'Source of mapping: human (manual), ai (algorithm), rule (business rule)';
