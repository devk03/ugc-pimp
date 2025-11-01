import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { LogoutButton } from '@/components/logout-button';
import { ThemeSwitcher } from '@/components/theme-switcher';
import { Separator } from '@/components/ui/separator';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();

  // Check if user is authenticated
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    redirect('/auth/login');
  }

  // Check if brand profile exists
  const { data: brandProfile } = await supabase
    .from('brand')
    .select('id, metadata')
    .eq('profile_id', user.id)
    .single();

  if (!brandProfile) {
    redirect('/onboarding');
  }

  const brandName =
    (brandProfile.metadata as any)?.company_name || 'Your Brand';

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background gradient wallpaper */}
      <div className="fixed inset-0 bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50 dark:from-purple-950/20 dark:via-pink-950/20 dark:to-orange-950/20 -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(168,85,247,0.08),transparent_50%)] dark:bg-[radial-gradient(circle_at_30%_20%,rgba(168,85,247,0.12),transparent_50%)] -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(236,72,153,0.08),transparent_50%)] dark:bg-[radial-gradient(circle_at_70%_80%,rgba(236,72,153,0.12),transparent_50%)] -z-10" />
      
      <div className="relative z-0">
        {/* Header */}
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div>
              <Link href="/dashboard" className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-pink-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg">
                  U
                </div>
                <div className="hidden sm:block">
                  <h1 className="text-lg font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">UGC Pimp</h1>
                  <p className="text-xs text-muted-foreground">{brandName}</p>
                </div>
              </Link>
            </div>

            <div className="flex items-center gap-4">
              <Button asChild className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white">
                <Link href="/dashboard/campaigns/new">+ New Campaign</Link>
              </Button>
              <ThemeSwitcher />
              <LogoutButton />
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-[65px] z-40">
          <div className="container mx-auto px-4">
            <div className="flex gap-8 overflow-x-auto">
              <Link
                href="/dashboard"
                className="px-1 py-4 border-b-2 border-transparent hover:border-purple-500 dark:hover:border-purple-400 text-sm font-medium text-muted-foreground hover:text-foreground whitespace-nowrap transition-colors"
              >
                Campaigns
              </Link>
              {/* Settings page coming soon */}
              {/* <Link
                href="/dashboard/settings"
                className="px-1 py-4 border-b-2 border-transparent hover:border-purple-500 dark:hover:border-purple-400 text-sm font-medium text-muted-foreground hover:text-foreground whitespace-nowrap transition-colors"
              >
                Settings
              </Link> */}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">{children}</main>
      </div>
    </div>
  );
}
