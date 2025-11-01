import { createClient } from '@/lib/supabase/server';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
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
    const { brand_id, name, product, description, spend, state, scheduled_start_date, scheduled_end_date } = body;

    if (!brand_id || !name || !product || !description || !spend) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Verify brand belongs to user
    const { data: brandData } = await supabase
      .from('brand')
      .select('id')
      .eq('id', brand_id)
      .eq('profile_id', user.id)
      .single();

    if (!brandData) {
      return NextResponse.json(
        { error: 'Brand not found or unauthorized' },
        { status: 403 }
      );
    }

    // Create campaign with state (defaults to DRAFT if not provided)
    const campaignDataToInsert: any = {
      brand_id,
      name,
      product,
      description,
      spend: parseFloat(spend),
      state: state || 'DRAFT',
      metadata: {
        created_at: new Date().toISOString(),
      },
    };

    // Add scheduled dates if provided and state is SCHEDULED
    if (state === 'SCHEDULED' || scheduled_start_date || scheduled_end_date) {
      if (scheduled_start_date) campaignDataToInsert.scheduled_start_date = scheduled_start_date;
      if (scheduled_end_date) campaignDataToInsert.scheduled_end_date = scheduled_end_date;
    }

    const { data: campaignData, error: campaignError } = await supabase
      .from('campaign')
      .insert(campaignDataToInsert)
      .select()
      .single();

    if (campaignError) {
      console.error('Database error:', campaignError);
      return NextResponse.json(
        { error: `Failed to create campaign: ${campaignError.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      campaign: campaignData,
    });
  } catch (err) {
    console.error('API error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'An error occurred' },
      { status: 500 }
    );
  }
}
