import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { DashboardClient } from './dashboard-client';

// Force dynamic rendering to ensure fresh data on every request
// This prevents Next.js from caching the dashboard page
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function DashboardPage() {
  const supabase = await createClient();

  // Check user authentication
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    redirect('/auth/login');
  }

  // Verify brand profile exists
  const { data: brandProfile, error: brandError } = await supabase
    .from('brand')
    .select('id')
    .eq('profile_id', user.id)
    .single();

  if (brandError || !brandProfile) {
    redirect('/auth/error?message=Brand profile not found');
  }

  // Render client component that handles all data fetching and real-time updates
  return <DashboardClient />;
}
