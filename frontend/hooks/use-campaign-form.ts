'use client';

import { useState } from 'react';
import { z } from 'zod';

// Define the campaign form schema
const campaignFormSchema = z.object({
  name: z.string().min(2, 'Campaign name must be at least 2 characters'),
  product: z.string().min(2, 'Product name must be at least 2 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  spend: z.string().transform((val) => {
    const num = parseFloat(val);
    if (isNaN(num) || num <= 0) {
      throw new Error('Spend must be a positive number');
    }
    return num;
  }),
});

export type CampaignFormData = z.infer<typeof campaignFormSchema>;

export interface CampaignFormState {
  name: string;
  product: string;
  description: string;
  spend: string;
  scheduled_start_date?: string;
  scheduled_end_date?: string;
  assets: File[];
}

const INITIAL_STATE: CampaignFormState = {
  name: '',
  product: '',
  description: '',
  spend: '',
  assets: [],
};

export function useCampaignForm() {
  const [formData, setFormData] = useState<CampaignFormState>(INITIAL_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const updateField = (field: keyof Omit<CampaignFormState, 'assets'>, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const addAssets = (files: File[]) => {
    setFormData((prev) => ({
      ...prev,
      assets: [...prev.assets, ...files],
    }));
  };

  const removeAsset = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      assets: prev.assets.filter((_, i) => i !== index),
    }));
  };

  const validateForm = (): boolean => {
    try {
      campaignFormSchema.parse({
        name: formData.name,
        product: formData.product,
        description: formData.description,
        spend: formData.spend,
      });
      return true;
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.issues[0].message);
      }
      return false;
    }
  };

  const uploadAssets = async (campaignId: string): Promise<void> => {
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('campaign_id', campaignId);

      formData.assets.forEach((file) => {
        formDataToSend.append('files', file);
      });

      const response = await fetch('/api/campaigns/upload-assets', {
        method: 'POST',
        body: formDataToSend,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Asset upload failed');
      }

      const data = await response.json();
      setUploadProgress(100);
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Asset upload failed');
    }
  };

  const submitCampaign = async (
    brandId: string,
    options?: {
      campaignId?: string;
      state?: 'DRAFT' | 'SCHEDULED';
      scheduled_start_date?: string;
      scheduled_end_date?: string;
    }
  ): Promise<boolean> => {
    return submitCampaignWithData(
      brandId,
      {
        name: formData.name,
        product: formData.product,
        description: formData.description,
        spend: formData.spend,
      },
      options
    );
  };

  const submitCampaignWithData = async (
    brandId: string,
    data: {
      name: string;
      product: string;
      description: string;
      spend: string;
    },
    options?: {
      campaignId?: string;
      state?: 'DRAFT' | 'SCHEDULED';
      scheduled_start_date?: string;
      scheduled_end_date?: string;
    }
  ): Promise<boolean> => {
    setError(null);
    setSuccess(false);

    // Validate the provided data
    try {
      campaignFormSchema.parse({
        name: data.name,
        product: data.product,
        description: data.description,
        spend: data.spend,
      });
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.issues[0].message);
      }
      return false;
    }

    setIsLoading(true);
    setUploadProgress(0);

    try {
      const isEdit = !!options?.campaignId;
      const url = isEdit 
        ? `/api/campaigns/${options.campaignId}`
        : '/api/campaigns/create';
      const method = isEdit ? 'PUT' : 'POST';

      // Create or update campaign via API route
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_id: brandId,
          name: data.name,
          product: data.product,
          description: data.description,
          spend: data.spend,
          state: options?.state || 'DRAFT',
          scheduled_start_date: options?.scheduled_start_date,
          scheduled_end_date: options?.scheduled_end_date,
        }),
      });

      if (!response.ok) {
        const responseData = await response.json();
        setError(responseData.error || `Failed to ${isEdit ? 'update' : 'create'} campaign`);
        return false;
      }

      const responseData = await response.json();
      const campaignId = responseData.campaign.id;

      // Upload assets if provided (only for new campaigns or if new assets added)
      if (formData.assets.length > 0) {
        setUploadProgress(10);
        await uploadAssets(campaignId);
      }

      setUploadProgress(100);
      setSuccess(true);
      if (!isEdit) {
        setFormData(INITIAL_STATE);
      }
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData(INITIAL_STATE);
    setError(null);
    setSuccess(false);
    setUploadProgress(0);
  };

  return {
    formData,
    isLoading,
    error,
    success,
    uploadProgress,
    updateField,
    addAssets,
    removeAsset,
    submitCampaign,
    submitCampaignWithData,
    resetForm,
    validateForm,
  };
}
