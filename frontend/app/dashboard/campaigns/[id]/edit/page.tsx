import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { CampaignForm } from '@/components/campaigns/campaign-form';

interface CampaignEditPageProps {
  params: Promise<{ id: string }>;
}

export default async function CampaignEditPage({
  params,
}: CampaignEditPageProps) {
  const { id: campaignId } = await params;
  const supabase = await createClient();

  // Check if user is authenticated
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    redirect('/auth/login');
  }

  // Get brand profile
  const { data: brandProfile } = await supabase
    .from('brand')
    .select('id')
    .eq('profile_id', user.id)
    .single();

  if (!brandProfile) {
    redirect('/onboarding');
  }

  // Fetch the campaign and verify ownership
  const { data: campaign, error: campaignError } = await supabase
    .from('campaign')
    .select('*')
    .eq('id', campaignId)
    .eq('brand_id', brandProfile.id)
    .single();

  if (campaignError || !campaign) {
    redirect('/dashboard');
  }

  // Only allow editing if campaign is DRAFT or SCHEDULED
  if (campaign.state !== 'DRAFT' && campaign.state !== 'SCHEDULED') {
    redirect(`/dashboard/campaigns/${campaignId}`);
  }

  return (
    <div className="py-8">
      <CampaignForm brandId={brandProfile.id} campaign={campaign} />
    </div>
  );
}

