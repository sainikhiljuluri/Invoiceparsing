-- Component 10: RAG System Database Tables
-- Create tables for conversation memory, analytics, and insights

-- Conversation Memory Table
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    user_query TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    intent VARCHAR(100),
    entities JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX(session_id),
    INDEX(timestamp)
);

-- RAG Analytics Table
CREATE TABLE IF NOT EXISTS rag_analytics (
    id SERIAL PRIMARY KEY,
    intent_type VARCHAR(100) NOT NULL,
    confidence DECIMAL(5,4),
    response_time DECIMAL(8,4),
    success BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX(intent_type),
    INDEX(timestamp)
);

-- Generated Insights Table
CREATE TABLE IF NOT EXISTS generated_insights (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    data JSONB,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX(type),
    INDEX(priority),
    INDEX(generated_at)
);

-- Anomaly Detections Table
CREATE TABLE IF NOT EXISTS anomaly_detections (
    id SERIAL PRIMARY KEY,
    anomaly_type VARCHAR(100) NOT NULL,
    product_id INTEGER REFERENCES products(id),
    vendor_id INTEGER REFERENCES vendors(id),
    severity VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    old_value DECIMAL(10,2),
    new_value DECIMAL(10,2),
    change_percent DECIMAL(8,4),
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    
    INDEX(anomaly_type),
    INDEX(severity),
    INDEX(detected_at),
    INDEX(resolved)
);

-- RAG System Configuration Table
CREATE TABLE IF NOT EXISTS rag_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default RAG configuration
INSERT INTO rag_config (config_key, config_value, description) VALUES
('model_name', 'claude-3-sonnet-20240229', 'Claude model for response generation'),
('embedding_model', 'all-MiniLM-L6-v2', 'Sentence transformer model for embeddings'),
('temperature', '0.7', 'Response generation temperature'),
('max_context_length', '4000', 'Maximum context length for responses'),
('anomaly_threshold', '20.0', 'Percentage threshold for anomaly detection'),
('insight_retention_days', '30', 'Days to retain generated insights')
ON CONFLICT (config_key) DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversation_memory_session_timestamp 
    ON conversation_memory(session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_rag_analytics_intent_timestamp 
    ON rag_analytics(intent_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_generated_insights_active_priority 
    ON generated_insights(is_active, priority, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_anomaly_detections_unresolved 
    ON anomaly_detections(resolved, detected_at DESC) WHERE resolved = FALSE;
