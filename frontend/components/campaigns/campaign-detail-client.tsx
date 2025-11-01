"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Users, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Database } from "@/lib/database.types";
import { format } from "date-fns";

// Helper function to extract TikTok metadata
function getTikTokInfo(metadata: any) {
  if (!metadata?.tiktok) return null;

  const tk = metadata.tiktok;
  return {
    username: tk.username,
    followerCount: tk.follower_count,
    heartCount: tk.heart_count,
    videoCount: tk.video_count,
    isVerified: tk.is_verified,
    avgLikesPerVideo: tk.avg_likes_per_video,
    likesToFollowersRatio: tk.likes_to_followers_ratio,
  };
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
}

interface CampaignDetailClientProps {
  campaign: Database["public"]["Tables"]["campaign"]["Row"];
  contacts: Array<{
    contact: Database["public"]["Tables"]["contact"]["Row"];
    assignment: Database["public"]["Tables"]["contact_campaign"]["Row"];
  }>;
}

const statusColors: Record<
  Database["public"]["Enums"]["contact_campaign_status"],
  string
> = {
  proposed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  negotiating:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  agreed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  delivered:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
};

const stateColors: Record<
  Database["public"]["Enums"]["campaign_state"],
  string
> = {
  DRAFT: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  SCHEDULED: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  ACTIVE: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  PAUSED: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  COMPLETED: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  ARCHIVED: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
  DELETED: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function CampaignDetailClient({
  campaign,
  contacts,
}: CampaignDetailClientProps) {
  const [expandedContactId, setExpandedContactId] = React.useState<string | null>(
    null
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Campaigns
          </Button>
        </Link>
        {(campaign.state === 'DRAFT' || campaign.state === 'SCHEDULED') && (
          <Link href={`/dashboard/campaigns/${campaign.id}/edit`}>
            <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white">
              Edit Campaign
            </Button>
          </Link>
        )}
      </div>

      {/* Campaign Details Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-3xl">{campaign.name}</CardTitle>
              <CardDescription>Campaign ID: {campaign.id}</CardDescription>
            </div>
            <Badge className={stateColors[campaign.state]}>
              {campaign.state}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Grid of campaign info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Campaign Information</h3>

              {campaign.product && (
                <div>
                  <p className="text-sm text-muted-foreground">Product</p>
                  <p className="text-base font-medium">{campaign.product}</p>
                </div>
              )}

              {campaign.description && (
                <div>
                  <p className="text-sm text-muted-foreground">Description</p>
                  <p className="text-base">{campaign.description}</p>
                </div>
              )}

              {campaign.spend !== null && (
                <div>
                  <p className="text-sm text-muted-foreground">Budget</p>
                  <p className="text-base font-medium">
                    ${campaign.spend.toFixed(2)}
                  </p>
                </div>
              )}
            </div>

            {/* Timeline Information */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Timeline</h3>

              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="text-base font-medium">
                  {format(new Date(campaign.created_at), "MMM dd, yyyy HH:mm")}
                </p>
              </div>

              {campaign.scheduled_start_date && (
                <div>
                  <p className="text-sm text-muted-foreground">
                    Scheduled Start
                  </p>
                  <p className="text-base font-medium">
                    {format(
                      new Date(campaign.scheduled_start_date),
                      "MMM dd, yyyy"
                    )}
                  </p>
                </div>
              )}

              {campaign.scheduled_end_date && (
                <div>
                  <p className="text-sm text-muted-foreground">
                    Scheduled End
                  </p>
                  <p className="text-base font-medium">
                    {format(new Date(campaign.scheduled_end_date), "MMM dd, yyyy")}
                  </p>
                </div>
              )}

              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="text-base font-medium">
                  {format(new Date(campaign.updated_at), "MMM dd, yyyy HH:mm")}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Assigned Contacts Card */}
      <Card>
        <CardHeader>
          <CardTitle>Assigned Contacts</CardTitle>
          <CardDescription>
            {contacts.length} contact{contacts.length !== 1 ? "s" : ""} assigned to
            this campaign
          </CardDescription>
        </CardHeader>
        <CardContent>
          {contacts.length > 0 ? (
            <div className="space-y-4">
              {contacts.map(({ contact, assignment }) => {
                const tikTokInfo = getTikTokInfo(contact.metadata);
                const isExpanded = expandedContactId === contact.id;

                return (
                  <div
                    key={contact.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    {/* Contact Row */}
                    <div
                      className="p-4 hover:bg-accent/50 cursor-pointer transition-colors"
                      onClick={() =>
                        setExpandedContactId(
                          isExpanded ? null : contact.id
                        )
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <div className="flex-1">
                              <h3 className="font-semibold">
                                {contact.firstname || ""} {contact.lastname || ""}
                                {!contact.firstname && !contact.lastname && "No Name"}
                              </h3>
                              {tikTokInfo && (
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant="outline" className="text-xs">
                                    TikTok
                                  </Badge>
                                  <p className="text-sm text-muted-foreground">
                                    {tikTokInfo.username}
                                  </p>
                                </div>
                              )}
                            </div>
                            <Badge className={statusColors[assignment.status]}>
                              {assignment.status.charAt(0).toUpperCase() +
                                assignment.status.slice(1)}
                            </Badge>
                          </div>
                        </div>
                        <ChevronDown
                          className={`h-5 w-5 transition-transform ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="border-t bg-muted/30 p-4 space-y-4">
                        {/* TikTok Stats */}
                        {tikTokInfo && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Followers
                              </p>
                              <p className="font-semibold">
                                {formatNumber(tikTokInfo.followerCount)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Avg Likes/Video
                              </p>
                              <p className="font-semibold">
                                {formatNumber(tikTokInfo.avgLikesPerVideo)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Videos
                              </p>
                              <p className="font-semibold">
                                {tikTokInfo.videoCount}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Engagement Rate
                              </p>
                              <p className="font-semibold">
                                {tikTokInfo.likesToFollowersRatio.toFixed(1)}%
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Contact Info */}
                        <div className="space-y-2">
                          {contact.platform && contact.platform.length > 0 && (
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Platforms
                              </p>
                              <div className="flex gap-1 flex-wrap mt-1">
                                {contact.platform.map((platform) => (
                                  <Badge
                                    key={platform}
                                    variant="outline"
                                    className="text-xs"
                                  >
                                    {platform}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {contact.tags && contact.tags.length > 0 && (
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Tags
                              </p>
                              <div className="flex gap-1 flex-wrap mt-1">
                                {contact.tags.map((tag) => (
                                  <Badge
                                    key={tag}
                                    variant="secondary"
                                    className="text-xs"
                                  >
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {(assignment.description ||
                            contact.description) && (
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Description
                              </p>
                              <p className="text-sm text-muted-foreground mt-1">
                                {assignment.description ||
                                  contact.description}
                              </p>
                            </div>
                          )}

                          {assignment.agreed_price && (
                            <div>
                              <p className="text-xs text-muted-foreground">
                                Agreed Price
                              </p>
                              <p className="text-sm font-semibold">
                                ${assignment.agreed_price}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                No contacts assigned to this campaign yet
              </p>
              <Link href="/dashboard">
                <Button variant="outline" size="sm">
                  Manage Campaigns
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
