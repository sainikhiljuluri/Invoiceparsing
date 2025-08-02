-- Complete Pricing System Database Tables
-- Run this in your Supabase SQL Editor

-- 1. Pricing Rules Table
CREATE TABLE IF NOT EXISTS pricing_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL,
    min_markup DECIMAL(5,2) NOT NULL,
    target_markup DECIMAL(5,2) NOT NULL,
    max_markup DECIMAL(5,2) NOT NULL,
    factors JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Product Pricing Table
CREATE TABLE IF NOT EXISTS product_pricing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    cost_price DECIMAL(10,2) NOT NULL,
    suggested_price DECIMAL(10,2) NOT NULL,
    min_price DECIMAL(10,2) NOT NULL,
    max_price DECIMAL(10,2) NOT NULL,
    markup_percentage DECIMAL(5,2),
    pricing_date DATE DEFAULT CURRENT_DATE,
    adjustments JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Competitor Prices Table
CREATE TABLE IF NOT EXISTS competitor_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_name VARCHAR(255) NOT NULL,
    competitor_name VARCHAR(100),
    competitor_price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    last_updated TIMESTAMP DEFAULT NOW(),
    source VARCHAR(100),
    active BOOLEAN DEFAULT TRUE
);

-- 4. Sales Data Table
CREATE TABLE IF NOT EXISTS sales_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    date DATE NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    revenue DECIMAL(10,2) GENERATED ALWAYS AS (quantity * price) STORED,
    profit DECIMAL(10,2) GENERATED ALWAYS AS (quantity * (price - cost)) STORED,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Pricing Recommendations Table (from our previous migration)
CREATE TABLE IF NOT EXISTS pricing_recommendations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    suggested_price DECIMAL(10,2) NOT NULL,
    min_price DECIMAL(10,2) NOT NULL,
    max_price DECIMAL(10,2) NOT NULL,
    markup_percentage DECIMAL(5,2) NOT NULL,
    category TEXT DEFAULT 'DEFAULT',
    confidence TEXT DEFAULT 'Medium',
    pricing_strategy TEXT,
    adjustments JSONB DEFAULT '[]'::jsonb,
    competitive_analysis JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add selling_price column to products table if not exists
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS selling_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS last_price_update TIMESTAMP;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_pricing_rules_category ON pricing_rules(category);
CREATE INDEX IF NOT EXISTS idx_product_pricing_product_id ON product_pricing(product_id);
CREATE INDEX IF NOT EXISTS idx_product_pricing_date ON product_pricing(pricing_date);
CREATE INDEX IF NOT EXISTS idx_competitor_prices_product ON competitor_prices(product_name);
CREATE INDEX IF NOT EXISTS idx_competitor_prices_active ON competitor_prices(active);
CREATE INDEX IF NOT EXISTS idx_sales_data_product_date ON sales_data(product_id, date);
CREATE INDEX IF NOT EXISTS idx_sales_data_date ON sales_data(date);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_invoice_id ON pricing_recommendations(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_product_id ON pricing_recommendations(product_id);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_product_name ON pricing_recommendations(product_name);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_category ON pricing_recommendations(category);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_is_active ON pricing_recommendations(is_active);
CREATE INDEX IF NOT EXISTS idx_pricing_recommendations_created_at ON pricing_recommendations(created_at);

-- Create unique constraint to prevent duplicate recommendations for same invoice+product
CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_recommendations_unique 
ON pricing_recommendations(invoice_id, product_name) 
WHERE is_active = true;

-- Add trigger to update updated_at timestamp for pricing_recommendations
CREATE OR REPLACE FUNCTION update_pricing_recommendations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_update_pricing_recommendations_updated_at
    BEFORE UPDATE ON pricing_recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_pricing_recommendations_updated_at();

-- Insert default pricing rules
INSERT INTO pricing_rules (category, min_markup, target_markup, max_markup, factors) VALUES
('RICE', 25.00, 35.00, 50.00, '{"volume_discount": true, "seasonal": false}'),
('FLOUR', 30.00, 40.00, 55.00, '{"bulk_pricing": true, "shelf_life": "medium"}'),
('SPICES', 60.00, 75.00, 100.00, '{"premium_category": true, "high_margin": true}'),
('SNACKS', 45.00, 60.00, 80.00, '{"impulse_buy": true, "marketing_heavy": true}'),
('FROZEN', 35.00, 45.00, 65.00, '{"storage_cost": true, "quick_turnover": true}'),
('SWEETS', 50.00, 65.00, 90.00, '{"seasonal": true, "festival_pricing": true}'),
('LENTILS', 30.00, 40.00, 55.00, '{"staple_food": true, "volume_discount": true}'),
('READY_TO_EAT', 40.00, 55.00, 75.00, '{"convenience_premium": true, "packaging_cost": true}'),
('BEVERAGES', 35.00, 50.00, 70.00, '{"brand_dependent": true, "seasonal": true}'),
('DEFAULT', 35.00, 45.00, 65.00, '{"general_category": true}')
ON CONFLICT (category) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE pricing_rules IS 'Stores markup rules by product category';
COMMENT ON TABLE product_pricing IS 'Stores historical pricing data for products';
COMMENT ON TABLE competitor_prices IS 'Stores competitor pricing information';
COMMENT ON TABLE sales_data IS 'Stores actual sales performance data';
COMMENT ON TABLE pricing_recommendations IS 'Stores AI-generated pricing recommendations from invoice processing';
