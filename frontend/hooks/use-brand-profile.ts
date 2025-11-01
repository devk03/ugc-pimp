'use client';

import { useEffect, useState } from 'react';

export interface BrandProfile {
  id: string;
  profile_id: string;
  metadata: {
    company_name: string;
    industry: string;
    logo_url?: string;
    contact?: {
      email: string;
      phone: string;
      address: string;
    };
    guidelines?: {
      tone: string;
      style: string;
      dos_donts: string;
    };
  };
}

export function useBrandProfile() {
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBrandProfile = async () => {
      try {
        setIsLoading(true);
        // Note: In a real app, you might fetch this from a server route
        // For now, brand data is fetched server-side in the layout
        setBrand(null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBrandProfile();
  }, []);

  return {
    brand,
    isLoading,
    error,
    hasProfile: brand !== null,
  };
}
