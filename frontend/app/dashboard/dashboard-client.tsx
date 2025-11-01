'use client';

import { useDashboardStats } from '@/hooks/use-dashboard-stats';
import { CampaignTable } from '@/components/campaigns/campaign-table';
import { CampaignEmptyState } from '@/components/campaigns/campaign-empty-state';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function DashboardClient() {
  const { data: stats, isLoading, error, refetch } = useDashboardStats();

  if (error) {
    return (
      <div className="space-y-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h3 className="font-semibold text-red-900">Error Loading Dashboard</h3>
          <p className="text-sm text-red-700 mt-1">{error.message}</p>
          <button
            onClick={refetch}
            className="mt-3 px-4 py-2 bg-red-900 text-white rounded hover:bg-red-800 text-sm"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-all duration-300 hover:shadow-lg group relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium">Total Campaigns</CardTitle>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 opacity-20 group-hover:opacity-30 transition-opacity" />
          </CardHeader>
          <CardContent className="relative z-10">
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">{stats?.totalCampaigns || 0}</div>
                <p className="text-xs text-muted-foreground">Active campaigns</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-pink-200 dark:border-pink-800 hover:border-pink-300 dark:hover:border-pink-700 transition-all duration-300 hover:shadow-lg group relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-pink-500/5 to-orange-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium">Total Spend</CardTitle>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-pink-500 to-orange-500 opacity-20 group-hover:opacity-30 transition-opacity" />
          </CardHeader>
          <CardContent className="relative z-10">
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-2xl font-bold bg-gradient-to-r from-pink-600 to-orange-600 bg-clip-text text-transparent">
                  ${(stats?.totalSpend || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </div>
                <p className="text-xs text-muted-foreground">Combined budget</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-orange-200 dark:border-orange-800 hover:border-orange-300 dark:hover:border-orange-700 transition-all duration-300 hover:shadow-lg group relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium">Active Creators</CardTitle>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-purple-500 opacity-20 group-hover:opacity-30 transition-opacity" />
          </CardHeader>
          <CardContent className="relative z-10">
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-purple-600 bg-clip-text text-transparent">{stats?.activeCreators || 0}</div>
                <p className="text-xs text-muted-foreground">Connected creators</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-all duration-300 hover:shadow-lg group relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-pink-500/5 to-orange-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium">Submissions</CardTitle>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500 opacity-20 group-hover:opacity-30 transition-opacity" />
          </CardHeader>
          <CardContent className="relative z-10">
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">{stats?.pendingSubmissions || 0}</div>
                <p className="text-xs text-muted-foreground">Pending review</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Campaigns Section */}
      <div>
        <Card className="border-0 shadow-lg">
          <CardHeader className="border-b">
            <CardTitle className="text-2xl bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Your Campaigns</CardTitle>
            <CardDescription>
              Manage and track all your UGC campaigns
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : stats?.campaigns && stats.campaigns.length > 0 ? (
              <CampaignTable campaigns={stats.campaigns} />
            ) : (
              <CampaignEmptyState />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
