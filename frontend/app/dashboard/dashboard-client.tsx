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
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-2 border-purple-400 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-300">Total Campaigns</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-3xl font-bold text-slate-900 dark:text-white">{stats?.totalCampaigns || 0}</div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">campaigns active</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-2 border-pink-400 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-300">Total Spend</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-3xl font-bold text-slate-900 dark:text-white">
                  ${(stats?.totalSpend || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">combined budget</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-2 border-orange-400 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-300">Active Creators</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-12 mb-2" />
                <Skeleton className="h-4 w-32" />
              </>
            ) : (
              <>
                <div className="text-3xl font-bold text-slate-900 dark:text-white">{stats?.activeCreators || 0}</div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">connected creators</p>
              </>
            )}
          </CardContent>
        </Card>

      </div>

      {/* Campaigns Section */}
      <div>
        <Card className="border-0 shadow-sm">
          <CardHeader className="border-b border-slate-200 dark:border-slate-700">
            <CardTitle className="text-2xl text-slate-900 dark:text-white">Your Campaigns</CardTitle>
            <CardDescription className="text-slate-500 dark:text-slate-400">
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
