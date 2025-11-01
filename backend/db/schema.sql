-- Ensure the uuid-ossp extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

-- Brand Table
-- Links to Supabase auth user
CREATE TABLE public.brand (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB
);
ALTER TABLE public.brand ENABLE ROW LEVEL SECURITY;

-- Campaign Table
-- Belongs to a Brand
CREATE TABLE public.campaign (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    brand_id UUID NOT NULL REFERENCES public.brand(id) ON DELETE CASCADE,
    product TEXT,
    asset_bucket_path TEXT,
    description TEXT,
    spend NUMERIC(12, 2),
    metadata JSONB
);
ALTER TABLE public.campaign ENABLE ROW LEVEL SECURITY;

-- Assets Table
-- Belongs to a Campaign
CREATE TABLE public.assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES public.campaign(id) ON DELETE CASCADE,
    asset_path TEXT NOT NULL,
    tag TEXT,
    metadata JSONB
);
ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;

-- Contact Table
-- Independent table for contacts/influencers
CREATE TABLE public.contact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    firstname TEXT,
    lastname TEXT,
    platform TEXT[],
    tags TEXT[],
    description TEXT,
    metadata JSONB
);
ALTER TABLE public.contact ENABLE ROW LEVEL SECURITY;

-- Contact_Campaign Table (Join Table)
-- Links Contacts and Campaigns (many-to-many)
CREATE TABLE public.contact_campaign (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES public.contact(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES public.campaign(id) ON DELETE CASCADE,
    description TEXT, -- Changed from 'Description uuid foreign key' as it was likely a typo
    metadata JSONB    -- Corrected from 'Metadata_jsonb' for consistency
);
ALTER TABLE public.contact_campaign ENABLE ROW LEVEL SECURITY;