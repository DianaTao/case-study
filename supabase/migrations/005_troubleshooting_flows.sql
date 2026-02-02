-- Create troubleshooting_flows table for externalized flow definitions
-- This allows non-engineers to iterate on flows by editing structured data

CREATE TABLE IF NOT EXISTS troubleshooting_flows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flow_id TEXT NOT NULL UNIQUE,
    appliance_type TEXT NOT NULL,
    symptom_key TEXT NOT NULL,
    name TEXT NOT NULL,
    steps JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_troubleshooting_flows_appliance ON troubleshooting_flows(appliance_type);
CREATE INDEX IF NOT EXISTS idx_troubleshooting_flows_symptom ON troubleshooting_flows(symptom_key);
CREATE INDEX IF NOT EXISTS idx_troubleshooting_flows_flow_id ON troubleshooting_flows(flow_id);

-- Example flow structure in steps JSONB:
-- [
--   {
--     "stepNumber": 1,
--     "question": "Is water reaching the ice maker?",
--     "options": [
--       {"label": "Yes", "value": "yes"},
--       {"label": "No", "value": "no"}
--     ],
--     "transitions": {
--       "yes": {"nextStep": 2},
--       "no": {"nextStep": 3}
--     }
--   }
-- ]
