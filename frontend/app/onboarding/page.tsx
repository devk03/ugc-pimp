import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { OnboardingForm } from '@/components/brand/onboarding-form';

export default async function OnboardingPage() {
  const supabase = await createClient();

  // Check if user is authenticated
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    redirect('/auth/login');
  }

  // Check if brand profile already exists
  const { data: existingBrand } = await supabase
    .from('brand')
    .select('id')
    .eq('profile_id', user.id)
    .single();

  // If brand profile exists, redirect to dashboard
  if (existingBrand) {
    redirect('/dashboard');
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background gradient wallpaper */}
      <div className="fixed inset-0 bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50 dark:from-purple-950/20 dark:via-pink-950/20 dark:to-orange-950/20 -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(168,85,247,0.08),transparent_50%)] dark:bg-[radial-gradient(circle_at_30%_20%,rgba(168,85,247,0.12),transparent_50%)] -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(236,72,153,0.08),transparent_50%)] dark:bg-[radial-gradient(circle_at_70%_80%,rgba(236,72,153,0.12),transparent_50%)] -z-10" />
      
      <div className="relative z-0 container mx-auto py-12 px-4">
        <OnboardingForm userEmail={user.email || ''} />
      </div>
    </div>
  );
}
