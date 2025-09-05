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

-- Marketplace Tables
CREATE TABLE IF NOT EXISTS catalog(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  price_cents INTEGER NOT NULL,
  type TEXT NOT NULL, -- template, mediapax_pack, script_bundle
  category TEXT, -- automotive, saas, local_services, etc
  payload_ref TEXT, -- S3 key or file reference
  preview_url TEXT,
  tags TEXT[], -- searchable tags
  active BOOLEAN DEFAULT true,
  featured BOOLEAN DEFAULT false,
  download_count INTEGER DEFAULT 0,
  rating DECIMAL(2,1) DEFAULT 0.0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS purchases(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  customer_email TEXT,
  item_id UUID REFERENCES catalog(id),
  amount_cents INTEGER NOT NULL,
  payment_provider TEXT DEFAULT 'stripe',
  payment_ref TEXT, -- stripe payment intent ID
  status TEXT DEFAULT 'pending', -- pending, completed, refunded
  download_url TEXT,
  download_expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID REFERENCES catalog(id),
  tenant_id TEXT,
  rating INTEGER CHECK (rating >= 1 AND rating <= 5),
  review_text TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_catalog_category ON catalog(category);
CREATE INDEX idx_catalog_type ON catalog(type);
CREATE INDEX idx_catalog_featured ON catalog(featured, active);
CREATE INDEX idx_purchases_tenant ON purchases(tenant_id);
CREATE INDEX idx_purchases_item ON purchases(item_id);

-- Referral System Tables
CREATE TABLE IF NOT EXISTS ref_codes(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  code TEXT UNIQUE NOT NULL,
  campaign_name TEXT,
  payout_cents INTEGER NOT NULL,
  payout_type TEXT DEFAULT 'fixed', -- fixed, percentage
  active BOOLEAN DEFAULT true,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref_attributions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT REFERENCES ref_codes(code),
  fingerprint TEXT NOT NULL, -- browser fingerprint
  ip_address INET,
  user_agent TEXT,
  referrer TEXT,
  first_seen TIMESTAMPTZ DEFAULT now(),
  last_seen TIMESTAMPTZ DEFAULT now(),
  conversion_value_cents INTEGER DEFAULT 0,
  converted BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS ref_conversions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT REFERENCES ref_codes(code),
  attribution_id UUID REFERENCES ref_attributions(id),
  amount_cents INTEGER NOT NULL,
  conversion_type TEXT, -- purchase, booking, subscription
  conversion_ref TEXT, -- external reference (purchase_id, booking_id, etc)
  payout_amount_cents INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ref_codes_tenant ON ref_codes(tenant_id);
CREATE INDEX idx_ref_attributions_code ON ref_attributions(code);
CREATE INDEX idx_ref_attributions_fingerprint ON ref_attributions(fingerprint);
CREATE INDEX idx_ref_conversions_code ON ref_conversions(code);