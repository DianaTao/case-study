-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enum types
CREATE TYPE appliance_type AS ENUM ('refrigerator', 'dishwasher');
CREATE TYPE compatibility_confidence AS ENUM ('exact', 'likely', 'unknown');
CREATE TYPE doc_type AS ENUM ('install', 'troubleshoot', 'faq', 'policy', 'qna');
CREATE TYPE intent_type AS ENUM (
  'part_lookup',
  'compatibility_check',
  'install_help',
  'troubleshoot',
  'cart_action',
  'order_support',
  'returns_policy',
  'out_of_scope'
);

-- Parts table
CREATE TABLE parts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_type appliance_type NOT NULL,
  partselect_number TEXT UNIQUE NOT NULL,
  manufacturer_number TEXT,
  name TEXT NOT NULL,
  brand TEXT,
  price_cents INTEGER NOT NULL,
  stock_status TEXT NOT NULL DEFAULT 'in_stock',
  image_url TEXT,
  product_url TEXT,
  description TEXT,
  rating DECIMAL(3,2),
  review_count INTEGER DEFAULT 0,
  has_install_instructions BOOLEAN DEFAULT false,
  has_videos BOOLEAN DEFAULT false,
  install_links TEXT[], -- Array of URLs
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Models table
CREATE TABLE models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_type appliance_type NOT NULL,
  model_number TEXT UNIQUE NOT NULL,
  brand TEXT,
  model_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Model-Part compatibility cross-reference
CREATE TABLE model_parts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_number TEXT NOT NULL,
  partselect_number TEXT NOT NULL,
  confidence compatibility_confidence NOT NULL DEFAULT 'exact',
  evidence_url TEXT,
  evidence_snippet TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(model_number, partselect_number)
);

-- Documents for RAG
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_type appliance_type,
  doc_type doc_type NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  content TEXT NOT NULL,
  embedding vector(1536), -- OpenAI ada-002 dimension
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Troubleshooting symptoms
CREATE TABLE troubleshooting_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_type appliance_type NOT NULL,
  symptom_key TEXT UNIQUE NOT NULL, -- e.g., 'ice_maker_not_working'
  symptom_text TEXT NOT NULL,
  decision_tree JSONB NOT NULL, -- Stores question flow
  likely_causes JSONB, -- Array of cause objects with part recommendations
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat sessions
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_type appliance_type,
  model_number TEXT,
  cart_id UUID,
  last_intent intent_type,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages (for history/analytics)
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  intent intent_type,
  tool_calls JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Carts
CREATE TABLE carts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id),
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cart items
CREATE TABLE cart_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID REFERENCES carts(id) ON DELETE CASCADE,
  partselect_number TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_parts_appliance ON parts(appliance_type);
CREATE INDEX idx_parts_partselect ON parts(partselect_number);
CREATE INDEX idx_parts_manufacturer ON parts(manufacturer_number);

CREATE INDEX idx_models_appliance ON models(appliance_type);
CREATE INDEX idx_models_number ON models(model_number);

CREATE INDEX idx_model_parts_model ON model_parts(model_number);
CREATE INDEX idx_model_parts_part ON model_parts(partselect_number);
CREATE INDEX idx_model_parts_confidence ON model_parts(confidence);

CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_appliance ON documents(appliance_type);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_sessions_created ON chat_sessions(created_at DESC);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_messages_created ON chat_messages(created_at DESC);

CREATE INDEX idx_carts_session ON carts(session_id);
CREATE INDEX idx_cart_items_cart ON cart_items(cart_id);

-- Functions for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_parts_updated_at BEFORE UPDATE ON parts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_models_updated_at BEFORE UPDATE ON models
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON chat_sessions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_carts_updated_at BEFORE UPDATE ON carts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
