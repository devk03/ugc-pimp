'use client';

import { useEffect, useState, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';
import { getDashboardStats, DashboardStats } from '@/app/dashboard/actions';

export interface UseDashboardStatsReturn {
  data: DashboardStats | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook that fetches dashboard statistics and subscribes to real-time updates
 * Updates automatically when:
 * - Campaigns are created, updated, or deleted
 * - Creators are connected to campaigns
 * - Submissions are created or updated
 */
export function useDashboardStats(): UseDashboardStatsReturn {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const supabase = createClient();

  // Fetch dashboard stats
  const fetchStats = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const stats = await getDashboardStats();
      setData(stats);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch dashboard stats');
      setError(error);
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchStats();

    // Get brand ID for subscriptions
    const setupSubscriptions = async () => {
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) return;

        // Get brand profile
        const { data: brandProfile } = await supabase
          .from('brand')
          .select('id')
          .eq('profile_id', user.id)
          .single();

        if (!brandProfile) return;

        // Subscribe to campaign changes
        const campaignSubscription = supabase
          .channel('campaigns')
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'campaign',
              filter: `brand_id=eq.${brandProfile.id}`,
            },
            () => {
              // Refetch stats when campaigns change
              fetchStats();
            }
          )
          .subscribe();

        // Subscribe to contact_campaign changes (creator-campaign relationships)
        const contactCampaignSubscription = supabase
          .channel('contact_campaigns')
          .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'contact_campaign',
            },
            () => {
              // Refetch stats when contact-campaign relationships change
              fetchStats();
            }
          )
          .subscribe();

        // Cleanup subscriptions on unmount
        return () => {
          supabase.removeChannel(campaignSubscription);
          supabase.removeChannel(contactCampaignSubscription);
        };
      } catch (err) {
        console.error('Error setting up real-time subscriptions:', err);
      }
    };

    const unsubscribe = setupSubscriptions();

    return () => {
      if (unsubscribe) {
        unsubscribe.then((unsub) => unsub?.());
      }
    };
  }, [fetchStats, supabase]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchStats,
  };
}
