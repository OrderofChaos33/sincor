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

CREATE TABLE IF NOT EXISTS buyer_reputation(
  buyer_id TEXT PRIMARY KEY,
  score INTEGER DEFAULT 80,
  total_leads INTEGER DEFAULT 0,
  returns INTEGER DEFAULT 0,
  avg_callback_time INTERVAL DEFAULT '1 hour',
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Booking Core Tables
CREATE TABLE IF NOT EXISTS resources(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  name TEXT NOT NULL,
  timezone TEXT DEFAULT 'America/Chicago',
  buffer_minutes INTEGER DEFAULT 15,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS slots(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id UUID REFERENCES resources(id),
  start_ts TIMESTAMPTZ NOT NULL,
  end_ts TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'available', -- available, booked, blocked
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS appointments(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id UUID REFERENCES resources(id),
  lead_id UUID REFERENCES leads(id),
  contact_name TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  start_ts TIMESTAMPTZ NOT NULL,
  end_ts TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'confirmed', -- confirmed, cancelled, completed
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_slots_resource_time ON slots(resource_id, start_ts, end_ts);
CREATE INDEX idx_appointments_resource_time ON appointments(resource_id, start_ts);

-- Subscription Management Tables
CREATE TABLE IF NOT EXISTS plans(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  price_cents INTEGER NOT NULL,
  interval_type TEXT DEFAULT 'month', -- month, year
  interval_count INTEGER DEFAULT 1, -- every 1 month, every 3 months, etc
  features JSONB DEFAULT '{}',
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscriptions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  customer_ref TEXT NOT NULL, -- external billing system customer ID
  plan_id UUID REFERENCES plans(id),
  stripe_subscription_id TEXT,
  status TEXT DEFAULT 'active', -- active, cancelled, past_due, trialing
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  trial_end TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_ref);
CREATE INDEX idx_subscriptions_tenant ON subscriptions(tenant_id);
CREATE INDEX idx_plans_tenant ON plans(tenant_id);