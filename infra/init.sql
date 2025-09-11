CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS leads(
  id UUID PRIMARY KEY,
  vertical TEXT,
  email TEXT,
  phone TEXT,
  ip INET,
  state TEXT,
  payload JSONB,
  contact JSONB,
  attributes JSONB,
  status TEXT DEFAULT 'received',
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

-- Analytics Materialized Views for Performance
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_funnel_daily AS
SELECT 
    COALESCE(l.vertical, 'unknown') as tenant,
    DATE(l.created_at) as date,
    COUNT(*) as received,
    COUNT(CASE WHEN l.payload->>'validation'->>'ok' = 'true' THEN 1 END) as cleaned,
    COUNT(CASE WHEN CAST(l.payload->>'score' AS INTEGER) > 0 THEN 1 END) as scored,
    COUNT(CASE WHEN dl.status = 'DELIVERED' THEN 1 END) as delivered
FROM leads l
LEFT JOIN delivery_ledger dl ON l.id = dl.lead_id
GROUP BY COALESCE(l.vertical, 'unknown'), DATE(l.created_at);

CREATE INDEX idx_mv_funnel_daily_tenant_date ON mv_funnel_daily(tenant, date);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_revenue_daily AS
SELECT 
    COALESCE(tenant_id, 'unknown') as tenant,
    DATE(created_at) as date,
    SUM(amount_cents) as gross_cents,
    COUNT(CASE WHEN status = 'refunded' THEN 1 END) as returns,
    COUNT(*) as total_transactions
FROM (
    -- Purchases
    SELECT tenant_id, created_at, amount_cents, status FROM purchases
    UNION ALL
    -- Subscriptions (estimated monthly revenue)
    SELECT tenant_id, created_at, 
           (SELECT price_cents FROM plans p WHERE p.id = s.plan_id), 
           status FROM subscriptions s
    UNION ALL
    -- Referral conversions
    SELECT 
        (SELECT tenant_id FROM ref_codes rc WHERE rc.code = c.code) as tenant_id,
        created_at, amount_cents, 'completed' as status
    FROM ref_conversions c
) revenue_sources
GROUP BY COALESCE(tenant_id, 'unknown'), DATE(created_at);

CREATE INDEX idx_mv_revenue_daily_tenant_date ON mv_revenue_daily(tenant, date);

-- Multi-Tenant System Tables
CREATE TABLE IF NOT EXISTS tenants(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_name TEXT UNIQUE NOT NULL,
  admin_email TEXT NOT NULL,
  admin_password_hash TEXT NOT NULL,
  plan TEXT DEFAULT 'starter',
  custom_domain TEXT,
  branding JSONB DEFAULT '{}',
  domain_settings JSONB DEFAULT '{}',
  feature_flags JSONB DEFAULT '{}',
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tenants_name ON tenants(tenant_name);
CREATE INDEX idx_tenants_domain ON tenants(custom_domain);
CREATE INDEX idx_tenants_active ON tenants(active);

-- Source Margin Requirements Table
CREATE TABLE IF NOT EXISTS source_margins(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  vertical TEXT NOT NULL,
  min_margin_pct DECIMAL(4,3) DEFAULT 0.200,  -- 20% default
  acquisition_cost_cents INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(source, vertical)
);

CREATE INDEX idx_source_margins_source_vertical ON source_margins(source, vertical);

-- Global Suppression Table
CREATE TABLE IF NOT EXISTS suppressions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL DEFAULT 'global',
  contact TEXT NOT NULL,
  contact_type TEXT NOT NULL CHECK (contact_type IN ('email', 'phone', 'sms')),
  reason TEXT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(tenant_id, contact, contact_type)
);

CREATE INDEX idx_suppressions_tenant_contact ON suppressions(tenant_id, contact, contact_type);
CREATE INDEX idx_suppressions_expires ON suppressions(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_suppressions_created ON suppressions(created_at);

-- Lead Recycling Exchange Tables
CREATE TABLE IF NOT EXISTS recycling_inventory(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  original_buyer_id TEXT NOT NULL,
  return_reason TEXT,
  original_price_cents INTEGER,
  recycling_price_cents INTEGER,
  min_bid_cents INTEGER,
  winning_bid_cents INTEGER,
  vertical TEXT,
  status TEXT DEFAULT 'available' CHECK (status IN ('available', 'sold', 'expired')),
  sold_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(lead_id)
);

CREATE TABLE IF NOT EXISTS recycling_bids(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  buyer_id TEXT NOT NULL,
  bid_cents INTEGER NOT NULL,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(lead_id, buyer_id)
);

CREATE INDEX idx_recycling_inventory_status ON recycling_inventory(status);
CREATE INDEX idx_recycling_inventory_vertical ON recycling_inventory(vertical);
CREATE INDEX idx_recycling_bids_lead ON recycling_bids(lead_id);
CREATE INDEX idx_recycling_bids_buyer ON recycling_bids(buyer_id);

-- Nurture Pack Tables  
CREATE TABLE IF NOT EXISTS nurture_packs(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  vertical TEXT NOT NULL,
  price_cents INTEGER NOT NULL,
  pack_type TEXT NOT NULL CHECK (pack_type IN ('email_sequence', 'sms_campaign', 'ad_creatives', 'scripts', 'full_funnel')),
  components JSONB,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pack_purchases(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id UUID REFERENCES nurture_packs(id),
  tenant_id TEXT NOT NULL,
  amount_cents INTEGER,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'refunded')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pack_installs(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
  pack_id UUID REFERENCES nurture_packs(id),
  tenant_id TEXT NOT NULL,
  customizations JSONB DEFAULT '{}',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pack_reviews(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pack_id UUID REFERENCES nurture_packs(id),
  tenant_id TEXT NOT NULL,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  review_text TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(pack_id, tenant_id)
);

CREATE INDEX idx_nurture_packs_vertical ON nurture_packs(vertical);
CREATE INDEX idx_nurture_packs_type ON nurture_packs(pack_type);
CREATE INDEX idx_pack_purchases_tenant ON pack_purchases(tenant_id);
CREATE INDEX idx_pack_installs_tenant ON pack_installs(tenant_id);

-- Partner API Tables
CREATE TABLE IF NOT EXISTS partner_accounts(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  contact_email TEXT NOT NULL,
  website TEXT,
  verticals TEXT[] NOT NULL,
  revenue_share_pct DECIMAL(4,3) NOT NULL CHECK (revenue_share_pct BETWEEN 0 AND 1),
  api_key TEXT UNIQUE NOT NULL,
  webhook_secret TEXT NOT NULL,
  active BOOLEAN DEFAULT true,
  last_seen TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS partner_leads(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partner_accounts(id),
  lead_id UUID REFERENCES leads(id),
  vertical TEXT NOT NULL,
  source TEXT,
  campaign_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(partner_id, lead_id)
);

CREATE TABLE IF NOT EXISTS partner_ledger(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partner_accounts(id),
  lead_id UUID REFERENCES leads(id),
  event_type TEXT NOT NULL,
  gross_cents INTEGER NOT NULL,
  revenue_share_cents INTEGER NOT NULL,
  revenue_share_pct DECIMAL(4,3) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_partner_accounts_api_key ON partner_accounts(api_key);
CREATE INDEX idx_partner_leads_partner ON partner_leads(partner_id);
CREATE INDEX idx_partner_leads_vertical ON partner_leads(vertical);
CREATE INDEX idx_partner_ledger_partner ON partner_ledger(partner_id);
CREATE INDEX idx_partner_ledger_created ON partner_ledger(created_at);

-- Chargeback Shield Tables
CREATE TABLE IF NOT EXISTS risk_transactions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id TEXT UNIQUE NOT NULL,
  customer_email TEXT NOT NULL,
  customer_ip INET,
  amount_cents INTEGER NOT NULL,
  risk_score DECIMAL(4,3) NOT NULL,
  risk_factors TEXT[] DEFAULT '{}',
  action_taken TEXT NOT NULL CHECK (action_taken IN ('allow', 'hold', 'deny', 'alternate_rail')),
  billing_address JSONB,
  payment_method JSONB,
  final_status TEXT CHECK (final_status IN ('completed', 'chargeback', 'refunded', 'fraud')),
  outcome_metadata JSONB,
  outcome_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_rules(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rules_json JSONB NOT NULL,
  version INTEGER NOT NULL,
  created_by TEXT DEFAULT 'system',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_risk_transactions_email ON risk_transactions(customer_email);
CREATE INDEX idx_risk_transactions_ip ON risk_transactions(customer_ip);
CREATE INDEX idx_risk_transactions_score ON risk_transactions(risk_score);
CREATE INDEX idx_risk_transactions_created ON risk_transactions(created_at);
CREATE INDEX idx_risk_transactions_action ON risk_transactions(action_taken);
CREATE INDEX idx_risk_rules_version ON risk_rules(version);

-- A/B Testing Lab Tables
CREATE TABLE IF NOT EXISTS ab_experiments(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  template_type TEXT NOT NULL, -- email_subject, email_body, sms_message, ad_creative
  control_template TEXT NOT NULL,
  variants JSONB, -- [{"name": "variant_a", "template": "..."}]
  traffic_split DECIMAL(4,3) DEFAULT 0.5,
  success_metric TEXT DEFAULT 'conversion_rate',
  min_sample_size INTEGER DEFAULT 100,
  max_duration_days INTEGER DEFAULT 30,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
  winner_variant TEXT,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ab_assignments(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID REFERENCES ab_experiments(id),
  user_id TEXT NOT NULL, -- lead_id, contact_id, etc
  variant_id TEXT NOT NULL,
  context JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(experiment_id, user_id)
);

CREATE TABLE IF NOT EXISTS ab_conversions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID REFERENCES ab_experiments(id),
  user_id TEXT NOT NULL,
  variant_id TEXT NOT NULL,
  event_type TEXT NOT NULL, -- open, click, convert
  value DECIMAL(10,4) DEFAULT 1.0,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ab_experiments_status ON ab_experiments(status);
CREATE INDEX idx_ab_experiments_type ON ab_experiments(template_type);
CREATE INDEX idx_ab_assignments_experiment ON ab_assignments(experiment_id);
CREATE INDEX idx_ab_assignments_user ON ab_assignments(user_id);
CREATE INDEX idx_ab_conversions_experiment ON ab_conversions(experiment_id);
CREATE INDEX idx_ab_conversions_user_variant ON ab_conversions(user_id, variant_id);

-- LTV Forecaster Tables
CREATE TABLE IF NOT EXISTS ltv_predictions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  customer_email TEXT,
  vertical TEXT NOT NULL,
  predicted_ltv DECIMAL(10,2) NOT NULL,
  actual_ltv DECIMAL(10,2),
  ltv_tier TEXT CHECK (ltv_tier IN ('low', 'medium', 'high')),
  features JSONB,
  model_version INTEGER,
  feedback_date TIMESTAMPTZ,
  timeframe_days INTEGER DEFAULT 365,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ltv_models(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vertical TEXT NOT NULL,
  version INTEGER DEFAULT 1,
  coefficients JSONB NOT NULL,
  features TEXT[] DEFAULT '{}',
  training_samples INTEGER DEFAULT 0,
  mse DECIMAL(10,4),
  r_squared DECIMAL(6,4),
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engagement_events(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_email TEXT NOT NULL,
  event_type TEXT NOT NULL, -- email_open, email_click, website_visit, booking_attempt
  event_data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ltv_predictions_vertical ON ltv_predictions(vertical);
CREATE INDEX idx_ltv_predictions_email ON ltv_predictions(customer_email);
CREATE INDEX idx_ltv_predictions_tier ON ltv_predictions(ltv_tier);
CREATE INDEX idx_ltv_models_vertical_active ON ltv_models(vertical, active);
CREATE INDEX idx_engagement_events_email ON engagement_events(customer_email);
CREATE INDEX idx_engagement_events_type ON engagement_events(event_type);

-- Kiosk Generator Tables
CREATE TABLE IF NOT EXISTS kiosk_campaigns(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  vertical TEXT NOT NULL,
  campaign_type TEXT NOT NULL CHECK (campaign_type IN ('book_now', 'gift_card', 'lead_capture', 'survey')),
  offer_title TEXT NOT NULL,
  offer_description TEXT,
  redirect_url TEXT,
  gift_card_value_cents INTEGER,
  expiry_days INTEGER DEFAULT 30,
  customization JSONB DEFAULT '{}',
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qr_codes(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES kiosk_campaigns(id),
  short_code TEXT UNIQUE NOT NULL,
  location TEXT,
  size INTEGER DEFAULT 200,
  include_logo BOOLEAN DEFAULT false,
  scan_count INTEGER DEFAULT 0,
  last_scanned TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kiosk_interactions(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES kiosk_campaigns(id),
  qr_short_code TEXT,
  interaction_type TEXT NOT NULL, -- scan, form_submit, booking, purchase
  interaction_data JSONB,
  user_agent TEXT,
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_kiosk_campaigns_tenant ON kiosk_campaigns(tenant_id);
CREATE INDEX idx_kiosk_campaigns_type ON kiosk_campaigns(campaign_type);
CREATE INDEX idx_qr_codes_campaign ON qr_codes(campaign_id);
CREATE INDEX idx_qr_codes_short_code ON qr_codes(short_code);
CREATE INDEX idx_kiosk_interactions_campaign ON kiosk_interactions(campaign_id);

-- Status Page & SLA Tables
CREATE TABLE IF NOT EXISTS service_health_checks(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name TEXT NOT NULL,
  is_healthy BOOLEAN NOT NULL,
  response_time_ms INTEGER DEFAULT 0,
  error_message TEXT,
  checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS status_incidents(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  service TEXT,
  severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status TEXT DEFAULT 'investigating' CHECK (status IN ('investigating', 'identified', 'monitoring', 'resolved')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS incident_updates(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID REFERENCES status_incidents(id),
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_sla_agreements(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT UNIQUE NOT NULL,
  sla_tier TEXT NOT NULL CHECK (sla_tier IN ('basic', 'premium', 'enterprise')),
  start_date TIMESTAMPTZ NOT NULL,
  monthly_fee_cents INTEGER DEFAULT 0,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sla_daily_metrics(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  date DATE NOT NULL,
  uptime_percentage DECIMAL(5,2) DEFAULT 100.00,
  avg_response_time_ms INTEGER DEFAULT 0,
  sla_tier TEXT NOT NULL,
  credit_percentage DECIMAL(5,4) DEFAULT 0.0000,
  credit_amount_cents INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(tenant_id, date)
);

CREATE INDEX idx_service_health_checks_service_time ON service_health_checks(service_name, checked_at DESC);
CREATE INDEX idx_status_incidents_status ON status_incidents(status);
CREATE INDEX idx_status_incidents_service ON status_incidents(service);
CREATE INDEX idx_incident_updates_incident ON incident_updates(incident_id);
CREATE INDEX idx_tenant_sla_agreements_tenant ON tenant_sla_agreements(tenant_id);
CREATE INDEX idx_sla_daily_metrics_tenant_date ON sla_daily_metrics(tenant_id, date);

-- Refresh function for materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_funnel_daily;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_revenue_daily;
END;
$$ LANGUAGE plpgsql;

-- Call Center Tables
CREATE TABLE IF NOT EXISTS calls(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  phone_number TEXT NOT NULL,
  direction TEXT DEFAULT 'outbound', -- outbound, inbound
  status TEXT DEFAULT 'queued', -- queued, dialing, connected, completed, failed, no_answer, voicemail, busy
  duration_seconds INTEGER DEFAULT 0,
  recording_url TEXT,
  notes TEXT,
  outcome TEXT, -- interested, not_interested, callback_requested, qualified, converted
  agent_id TEXT,
  provider_call_id TEXT, -- Twilio SID or provider reference
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_calls_lead_id ON calls(lead_id);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_calls_agent_id ON calls(agent_id);
CREATE INDEX idx_calls_created_at ON calls(created_at);