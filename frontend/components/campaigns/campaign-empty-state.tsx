'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Zap } from 'lucide-react';

export function CampaignEmptyState() {
  return (
    <Card className="border-dashed">
      <CardHeader className="text-center">
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-muted rounded-full">
            <Zap className="w-6 h-6 text-muted-foreground" />
          </div>
        </div>
        <CardTitle>No campaigns yet</CardTitle>
        <CardDescription>
          Get started by creating your first UGC campaign to connect with creators
        </CardDescription>
      </CardHeader>
      <CardContent className="flex justify-center">
        <Button asChild>
          <Link href="/dashboard/campaigns/new">Create Your First Campaign</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
