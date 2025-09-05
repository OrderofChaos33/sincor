CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS leads(
  id UUID PRIMARY KEY,
  vertical TEXT,
  email TEXT,
  phone TEXT,
  ip INET,
  state TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consent_artifacts(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  ts TIMESTAMPTZ NOT NULL,
  ip INET,
  referrer TEXT,
  form_html TEXT,
  sha256_hex TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS delivery_ledger(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  destination TEXT,
  status TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);