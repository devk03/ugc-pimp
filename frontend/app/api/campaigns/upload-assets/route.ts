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

    // Get form data
    const formData = await request.formData();
    const campaign_id = formData.get('campaign_id') as string;
    const files = formData.getAll('files') as File[];

    if (!campaign_id || !files || files.length === 0) {
      return NextResponse.json(
        { error: 'Missing campaign_id or files' },
        { status: 400 }
      );
    }

    // Verify campaign exists and belongs to user's brand
    const { data: campaignData } = await supabase
      .from('campaign')
      .select('brand_id')
      .eq('id', campaign_id)
      .single();

    if (!campaignData) {
      return NextResponse.json(
        { error: 'Campaign not found' },
        { status: 404 }
      );
    }

    // Verify brand belongs to user
    const { data: brandData } = await supabase
      .from('brand')
      .select('id')
      .eq('id', campaignData.brand_id)
      .eq('profile_id', user.id)
      .single();

    if (!brandData) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 403 }
      );
    }

    // Upload files and create asset records
    const uploadedAssets = [];

    for (const file of files) {
      const buffer = await file.arrayBuffer();
      const fileName = `${campaign_id}/${Date.now()}-${Math.random().toString(36).slice(2)}-${file.name}`;

      // Upload to storage
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('campaign-assets')
        .upload(fileName, buffer, {
          cacheControl: '3600',
          upsert: false,
          contentType: file.type,
        });

      if (uploadError) {
        console.error('Storage error:', uploadError);
        continue;
      }

      // Create asset record in database
      const { data: assetRecord, error: insertError } = await supabase
        .from('assets')
        .insert({
          campaign_id,
          asset_path: uploadData.path,
          tag: file.type.startsWith('image/') ? 'image' : 'video',
          metadata: {
            filename: file.name,
            size: file.size,
            type: file.type,
          },
        })
        .select()
        .single();

      if (!insertError && assetRecord) {
        uploadedAssets.push(assetRecord);
      }
    }

    return NextResponse.json({
      success: true,
      assets: uploadedAssets,
      uploaded_count: uploadedAssets.length,
    });
  } catch (err) {
    console.error('API error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'An error occurred' },
      { status: 500 }
    );
  }
}
