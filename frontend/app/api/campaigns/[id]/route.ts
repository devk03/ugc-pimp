import { createClient } from '@/lib/supabase/server';
import { NextRequest, NextResponse } from 'next/server';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: campaignId } = await params;
    const supabase = await createClient();

    // Get current user
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser();

    if (userError || !user) {
      return NextResponse.json(
        { error: 'User not authenticated' },
        { status: 401 }
      );
    }

    // Get brand profile
    const { data: brandProfile } = await supabase
      .from('brand')
      .select('id')
      .eq('profile_id', user.id)
      .single();

    if (!brandProfile) {
      return NextResponse.json(
        { error: 'Brand profile not found' },
        { status: 403 }
      );
    }

    // Fetch campaign and verify ownership and state
    const { data: campaign, error: campaignError } = await supabase
      .from('campaign')
      .select('id, state, brand_id')
      .eq('id', campaignId)
      .eq('brand_id', brandProfile.id)
      .single();

    if (campaignError || !campaign) {
      return NextResponse.json(
        { error: 'Campaign not found or unauthorized' },
        { status: 404 }
      );
    }

    // Only allow deletion if campaign is DRAFT or SCHEDULED
    if (campaign.state !== 'DRAFT' && campaign.state !== 'SCHEDULED') {
      return NextResponse.json(
        { error: `Cannot delete campaign with state: ${campaign.state}. Only DRAFT or SCHEDULED campaigns can be deleted.` },
        { status: 400 }
      );
    }

    // Delete the campaign
    const { error: deleteError } = await supabase
      .from('campaign')
      .delete()
      .eq('id', campaignId)
      .eq('brand_id', brandProfile.id);

    if (deleteError) {
      console.error('Database error:', deleteError);
      return NextResponse.json(
        { error: `Failed to delete campaign: ${deleteError.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: 'Campaign deleted successfully',
    });
  } catch (err) {
    console.error('API error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'An error occurred' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: campaignId } = await params;
    const supabase = await createClient();

    // Get current user
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser();

    if (userError || !user) {
      return NextResponse.json(
        { error: 'User not authenticated' },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await request.json();
    const { name, product, description, spend, state, scheduled_start_date, scheduled_end_date } = body;

    // Get brand profile
    const { data: brandProfile } = await supabase
      .from('brand')
      .select('id')
      .eq('profile_id', user.id)
      .single();

    if (!brandProfile) {
      return NextResponse.json(
        { error: 'Brand profile not found' },
        { status: 403 }
      );
    }

    // Verify campaign ownership
    const { data: existingCampaign, error: campaignError } = await supabase
      .from('campaign')
      .select('id, state, brand_id')
      .eq('id', campaignId)
      .eq('brand_id', brandProfile.id)
      .single();

    if (campaignError || !existingCampaign) {
      return NextResponse.json(
        { error: 'Campaign not found or unauthorized' },
        { status: 404 }
      );
    }

    // Only allow editing if campaign is DRAFT or SCHEDULED
    if (existingCampaign.state !== 'DRAFT' && existingCampaign.state !== 'SCHEDULED') {
      return NextResponse.json(
        { error: `Cannot edit campaign with state: ${existingCampaign.state}. Only DRAFT or SCHEDULED campaigns can be edited.` },
        { status: 400 }
      );
    }

    // Build update object - only include fields that are provided
    const updateData: any = {
      updated_at: new Date().toISOString(),
    };

    if (name !== undefined) updateData.name = name;
    if (product !== undefined) updateData.product = product;
    if (description !== undefined) updateData.description = description;
    if (spend !== undefined) updateData.spend = parseFloat(spend);
    if (state !== undefined) updateData.state = state;
    if (scheduled_start_date !== undefined) updateData.scheduled_start_date = scheduled_start_date || null;
    if (scheduled_end_date !== undefined) updateData.scheduled_end_date = scheduled_end_date || null;

    // Update campaign
    const { data: updatedCampaign, error: updateError } = await supabase
      .from('campaign')
      .update(updateData)
      .eq('id', campaignId)
      .eq('brand_id', brandProfile.id)
      .select()
      .single();

    if (updateError) {
      console.error('Database error:', updateError);
      return NextResponse.json(
        { error: `Failed to update campaign: ${updateError.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      campaign: updatedCampaign,
    });
  } catch (err) {
    console.error('API error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'An error occurred' },
      { status: 500 }
    );
  }
}

