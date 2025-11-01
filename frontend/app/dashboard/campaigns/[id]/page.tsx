import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { CampaignDetailClient } from "@/components/campaigns/campaign-detail-client";

interface CampaignDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CampaignDetailPage({
  params,
}: CampaignDetailPageProps) {
  const { id: campaignId } = await params;
  const supabase = await createClient();

  // Check authentication
  const { data: authData, error: authError } = await supabase.auth.getClaims();
  if (authError || !authData?.claims) {
    redirect("/auth/login");
  }

  const userId = authData.claims.sub;

  // Fetch user's brand(s)
  const { data: brandData, error: brandError } = await supabase
    .from("brand")
    .select("id")
    .eq("profile_id", userId)
    .single();

  if (brandError || !brandData) {
    redirect("/onboarding");
  }

  // Fetch the campaign and verify ownership
  const { data: campaign, error: campaignError } = await supabase
    .from("campaign")
    .select("*")
    .eq("id", campaignId)
    .eq("brand_id", brandData.id)
    .single();

  if (campaignError || !campaign) {
    redirect("/dashboard");
  }

  // Fetch contacts assigned to this campaign
  const { data: contactAssignments, error: contactsError } = await supabase
    .from("contact_campaign")
    .select(
      `
      id,
      description,
      created_at,
      updated_at,
      contact:contact_id (
        id,
        firstname,
        lastname,
        platform,
        tags,
        description,
        metadata,
        created_at,
        updated_at
      )
    `
    )
    .eq("campaign_id", campaignId);

  if (contactsError) {
    console.error("Error fetching contacts:", contactsError);
  }

  // Transform the data for the client component
  const contacts = (contactAssignments || []).map((assignment: any) => ({
    contact: assignment.contact,
    assignment: {
      id: assignment.id,
      contact_id: assignment.contact.id,
      campaign_id: campaignId,
      description: assignment.description,
      created_at: assignment.created_at,
      updated_at: assignment.updated_at,
      metadata: null,
    },
  }));

  return (
    <div className="container py-8">
      <CampaignDetailClient campaign={campaign} contacts={contacts} />
    </div>
  );
}
