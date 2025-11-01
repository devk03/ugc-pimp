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

    // Check if brand profile already exists
    const { data: existingBrand } = await supabase
      .from('brand')
      .select('id')
      .eq('profile_id', user.id)
      .single();

    if (existingBrand) {
      return NextResponse.json(
        { error: 'Brand profile already exists' },
        { status: 400 }
      );
    }

    // Parse request body
    const body = await request.json();
    const {
      company_name,
      industry,
      phone,
      tone,
      dos_donts,
      logo_url,
    } = body;

    // Create brand profile
    const brandMetadata = {
      company_name,
      industry,
      logo_url: logo_url || null,
      contact: {
        phone: phone || null,
      },
      guidelines: {
        tone,
        dos_donts,
      },
    };

    const { data, error } = await supabase
      .from('brand')
      .insert({
        profile_id: user.id,
        metadata: brandMetadata,
      })
      .select()
      .single();

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { error: `Failed to create brand profile: ${error.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      brand: data,
    });
  } catch (err) {
    console.error('API error:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'An error occurred' },
      { status: 500 }
    );
  }
}
