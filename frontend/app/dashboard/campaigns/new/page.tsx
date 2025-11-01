import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { CampaignForm } from '@/components/campaigns/campaign-form';

export default async function NewCampaignPage() {
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

  return (
    <div className="py-8">
      <CampaignForm brandId={brandProfile.id} />
    </div>
  );
}
