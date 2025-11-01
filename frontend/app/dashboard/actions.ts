'use server';

import { createClient } from '@/lib/supabase/server';
import { revalidatePath } from 'next/cache';

export interface DashboardStats {
  totalCampaigns: number;
  totalSpend: number;
  activeCreators: number;
  pendingSubmissions: number;
  campaigns: any[];
}

/**
 * Fetches all dashboard statistics for the authenticated user's brand
 * This includes: campaigns, spend, active creators, and pending submissions
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    const supabase = await createClient();

    // Get authenticated user
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser();

    if (userError || !user) {
      throw new Error('User not authenticated');
    }

    // Get brand profile
    const { data: brandProfile, error: brandError } = await supabase
      .from('brand')
      .select('id')
      .eq('profile_id', user.id)
      .single();

    if (brandError || !brandProfile) {
      throw new Error('Brand profile not found');
    }

    // Get campaigns for this brand
    const { data: campaigns, error: campaignsError } = await supabase
      .from('campaign')
      .select('*')
      .eq('brand_id', brandProfile.id);

    if (campaignsError) {
      throw campaignsError;
    }

    // Calculate campaign stats
    const totalCampaigns = campaigns?.length || 0;
    const totalSpend = campaigns?.reduce((sum: number, c: any) => sum + (c.spend || 0), 0) || 0;

    // Get all contact_campaign records for this brand's campaigns
    const { data: campaignIds } = await supabase
      .from('campaign')
      .select('id')
      .eq('brand_id', brandProfile.id);

    let activeCreators = 0;
    let pendingSubmissions = 0;

    if (campaignIds && campaignIds.length > 0) {
      const campaignIdsList = campaignIds.map((c) => c.id);

      // Get all contact_campaign relationships for these campaigns
      const { data: contactCampaigns, error: contactCampaignError } = await supabase
        .from('contact_campaign')
        .select('contact_id, metadata')
        .in('campaign_id', campaignIdsList);

      if (!contactCampaignError && contactCampaigns) {
        // Count unique creators (contact_ids)
        const uniqueCreatorIds = new Set(contactCampaigns.map((cc) => cc.contact_id));
        activeCreators = uniqueCreatorIds.size;

        // Count pending submissions - these are contact_campaign records where
        // the metadata doesn't have a completion status or status is 'pending'
        pendingSubmissions = contactCampaigns.filter((cc) => {
          const metadata = cc.metadata as any;
          return !metadata?.status || metadata?.status === 'pending';
        }).length;
      }
    }

    return {
      totalCampaigns,
      totalSpend,
      activeCreators,
      pendingSubmissions,
      campaigns: campaigns || [],
    };
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    throw error;
  }
}

/**
 * Revalidates the dashboard page to refresh cached data
 */
export async function revalidateDashboard() {
  try {
    revalidatePath('/dashboard');
  } catch (error) {
    console.error('Error revalidating dashboard:', error);
    throw error;
  }
}
