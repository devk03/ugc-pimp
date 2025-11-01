'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MoreHorizontal, Trash2, Eye } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import Link from 'next/link';
import { useState } from 'react';
import { format } from 'date-fns';

interface Campaign {
  id: string;
  name: string;
  product: string;
  description: string;
  spend: number;
  state?: 'DRAFT' | 'SCHEDULED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED' | 'DELETED';
  created_at?: string;
}

interface CampaignTableProps {
  campaigns: Campaign[];
}

const stateColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  SCHEDULED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  ACTIVE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  PAUSED: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  COMPLETED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  ARCHIVED: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  DELETED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

export function CampaignTable({ campaigns }: CampaignTableProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const canEdit = (state?: string) => {
    return state === 'DRAFT' || state === 'SCHEDULED';
  };

  const canDelete = (state?: string) => {
    return state === 'DRAFT' || state === 'SCHEDULED';
  };

  const handleDelete = async (campaignId: string, campaignName: string) => {
    if (!confirm(`Are you sure you want to delete "${campaignName}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingId(campaignId);
    try {
      const response = await fetch(`/api/campaigns/${campaignId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        alert(data.error || 'Failed to delete campaign');
        return;
      }

      // Refresh the page to update the list
      window.location.reload();
    } catch (error) {
      console.error('Error deleting campaign:', error);
      alert('An error occurred while deleting the campaign');
    } finally {
      setDeletingId(null);
    }
  };

  const handleOpenDetails = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setSelectedCampaign(null);
  };

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Campaign Name</TableHead>
            <TableHead>Product</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Budget</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {campaigns.map((campaign) => (
            <TableRow
              key={campaign.id}
              className="hover:bg-muted/50 cursor-pointer"
              onClick={() => handleOpenDetails(campaign)}
            >
              <TableCell className="font-medium">{campaign.name}</TableCell>
              <TableCell>{campaign.product}</TableCell>
              <TableCell>
                <Badge className={stateColors[campaign.state || 'DRAFT']}>
                  {campaign.state || 'DRAFT'}
                </Badge>
              </TableCell>
              <TableCell>{formatCurrency(campaign.spend)}</TableCell>
              <TableCell>{formatDate(campaign.created_at)}</TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                      <Link href={`/dashboard/campaigns/${campaign.id}`}>View Details</Link>
                    </DropdownMenuItem>
                    {canEdit(campaign.state) && (
                      <DropdownMenuItem asChild>
                        <Link href={`/dashboard/campaigns/${campaign.id}/edit`}>Edit</Link>
                      </DropdownMenuItem>
                    )}
                    {canDelete(campaign.state) && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-red-600 focus:text-red-600"
                          onClick={() => handleDelete(campaign.id, campaign.name)}
                          disabled={deletingId === campaign.id}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          {deletingId === campaign.id ? 'Deleting...' : 'Delete'}
                        </DropdownMenuItem>
                      </>
                    )}
                    {!canDelete(campaign.state) && campaign.state === 'ACTIVE' && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem disabled className="text-muted-foreground">
                          Cannot delete active campaigns
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Campaign Details Modal */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          {selectedCampaign && (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl">{selectedCampaign.name}</DialogTitle>
                <DialogDescription className="text-base">
                  Campaign ID: {selectedCampaign.id}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {/* Status and Budget Row */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Status</p>
                    <Badge className={stateColors[selectedCampaign.state || 'DRAFT']}>
                      {selectedCampaign.state || 'DRAFT'}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Budget</p>
                    <p className="text-lg font-semibold">
                      {formatCurrency(selectedCampaign.spend)}
                    </p>
                  </div>
                </div>

                {/* Product */}
                {selectedCampaign.product && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Product</p>
                    <p className="text-base">{selectedCampaign.product}</p>
                  </div>
                )}

                {/* Description */}
                {selectedCampaign.description && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Description</p>
                    <p className="text-base text-foreground">{selectedCampaign.description}</p>
                  </div>
                )}

                {/* Created Date */}
                {selectedCampaign.created_at && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Created</p>
                    <p className="text-base">
                      {format(new Date(selectedCampaign.created_at), 'MMM dd, yyyy HH:mm')}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2 pt-4">
                  <Button asChild>
                    <Link href={`/dashboard/campaigns/${selectedCampaign.id}`}>
                      <Eye className="h-4 w-4 mr-2" />
                      View Full Details
                    </Link>
                  </Button>
                  {canEdit(selectedCampaign.state) && (
                    <Button asChild variant="outline">
                      <Link href={`/dashboard/campaigns/${selectedCampaign.id}/edit`}>
                        Edit Campaign
                      </Link>
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
