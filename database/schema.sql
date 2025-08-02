-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Vendors table
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    country VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    brand VARCHAR(255),
    category VARCHAR(255),
    barcode VARCHAR(50),
    sku VARCHAR(100),
    cost DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    embedding vector(384),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id),
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    invoice_date DATE,
    vendor_name VARCHAR(255),
    total_amount DECIMAL(10, 2),
    subtotal DECIMAL(10, 2),
    tax_amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    processing_status VARCHAR(50) DEFAULT 'pending',
    status_message TEXT,
    products_found INTEGER,
    products_matched INTEGER,
    alerts_generated INTEGER,
    extraction_method VARCHAR(50),
    processing_time_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Invoice items table
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    line_number INTEGER,
    invoice_product_name VARCHAR(500) NOT NULL,
    product_id UUID REFERENCES products(id),
    quantity DECIMAL(10, 2),
    units DECIMAL(10, 2),
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(10, 2),
    cost_per_unit DECIMAL(10, 2),
    match_confidence DECIMAL(3, 2),
    match_strategy VARCHAR(50),
    routing VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Price history table
CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    vendor_id UUID REFERENCES vendors(id),
    invoice_id UUID REFERENCES invoices(id),
    invoice_number VARCHAR(100),
    old_cost DECIMAL(10, 2),
    new_cost DECIMAL(10, 2),
    change_percentage DECIMAL(5, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Price alerts table
CREATE TABLE IF NOT EXISTS price_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    invoice_id UUID REFERENCES invoices(id),
    alert_type VARCHAR(50),
    alert_message TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'pending',
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Human review queue table
CREATE TABLE IF NOT EXISTS human_review_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_item_id UUID REFERENCES invoice_items(id),
    suggested_matches JSONB DEFAULT '[]',
    confidence_scores JSONB DEFAULT '[]',
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'pending',
    reviewed_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE
);

-- Processing queue table
CREATE TABLE IF NOT EXISTS processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID UNIQUE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'queued',
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_processing_queue_status ON processing_queue(status);
CREATE INDEX IF NOT EXISTS idx_processing_queue_priority ON processing_queue(priority);
CREATE INDEX IF NOT EXISTS idx_invoices_processing_status ON invoices(processing_status);
CREATE INDEX IF NOT EXISTS idx_invoices_vendor_id ON invoices(vendor_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_product_id ON invoice_items(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_status ON price_alerts(status);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name);

-- Helper functions
CREATE OR REPLACE FUNCTION get_processing_stats()
RETURNS TABLE (
    total_processed BIGINT,
    successful BIGINT,
    failed BIGINT,
    pending BIGINT,
    average_processing_time FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_processed,
        COUNT(*) FILTER (WHERE processing_status = 'completed') as successful,
        COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
        COUNT(*) FILTER (WHERE processing_status IN ('queued', 'processing')) as pending,
        AVG(processing_time_seconds) as average_processing_time
    FROM invoices;
END;
$$ LANGUAGE plpgsql;

-- Insert sample vendors
INSERT INTO vendors (name, currency, country) VALUES 
    ('NIKHIL DISTRIBUTORS', 'INR', 'India'),
    ('CHETAK SAN FRANCISCO LLC', 'USD', 'USA'),
    ('RAJA FOODS', 'USD', 'USA'),
    ('JK WHOLESALE', 'USD', 'USA')
ON CONFLICT (name) DO NOTHING;

-- Insert sample products for testing
INSERT INTO products (name, brand, category, cost, currency) VALUES 
    ('DEEP CASHEW WHOLE 7OZ', 'DEEP', 'Nuts', 30.00, 'INR'),
    ('HALDIRAM BHUJIA 200G', 'HALDIRAM', 'Snacks', 45.00, 'INR'),
    ('MTR SAMBAR POWDER 200G', 'MTR', 'Spices', 25.00, 'INR'),
    ('SWAD BASMATI RICE 10LB', 'SWAD', 'Rice', 15.99, 'USD'),
    ('LAXMI TEA 500G', 'LAXMI', 'Beverages', 8.50, 'USD')
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- Success message
SELECT 'Database schema created successfully! Ready for invoice processing.' as message;