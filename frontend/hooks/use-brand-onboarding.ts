'use client';

import { useState } from 'react';
import { z } from 'zod';

// Define validation schemas for each step
const basicInfoSchema = z.object({
  company_name: z.string().min(2, 'Company name must be at least 2 characters'),
  industry: z.string().min(1, 'Please select an industry'),
  logo_file: z.instanceof(File).optional(),
});

const contactDetailsSchema = z.object({
  phone: z.string().min(10, 'Phone must be at least 10 characters').optional().or(z.literal('')),
});

const brandGuidelinesSchema = z.object({
  tone: z.string().min(10, 'Tone description must be at least 10 characters'),
  dos_donts: z.string().min(10, 'Do\'s and Don\'ts must be at least 10 characters'),
});

export interface BrandOnboardingState {
  company_name: string;
  industry: string;
  phone: string;
  tone: string;
  dos_donts: string;
  logo_file: File | null;
}

const INITIAL_STATE: BrandOnboardingState = {
  company_name: '',
  industry: '',
  phone: '',
  tone: '',
  dos_donts: '',
  logo_file: null,
};

export function useBrandOnboarding() {
  const [formData, setFormData] = useState<BrandOnboardingState>(INITIAL_STATE);
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const updateField = (field: keyof BrandOnboardingState, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const validateCurrentStep = (): boolean => {
    try {
      setError(null);

      if (currentStep === 1) {
        basicInfoSchema.parse({
          company_name: formData.company_name,
          industry: formData.industry,
          logo_file: formData.logo_file || undefined,
        });
      } else if (currentStep === 2) {
        contactDetailsSchema.parse({
          phone: formData.phone,
        });
      } else if (currentStep === 3) {
        brandGuidelinesSchema.parse({
          tone: formData.tone,
          dos_donts: formData.dos_donts,
        });
      }
      return true;
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.issues[0].message);
      }
      return false;
    }
  };

  const goToNextStep = (): boolean => {
    if (!validateCurrentStep()) {
      return false;
    }
    if (currentStep < 3) {
      setCurrentStep((prev) => (prev + 1) as 1 | 2 | 3);
    }
    return true;
  };

  const goToPreviousStep = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as 1 | 2 | 3);
      setError(null);
    }
  };

  const uploadLogo = async (): Promise<string | null> => {
    if (!formData.logo_file) {
      return null;
    }

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('file', formData.logo_file);

      const response = await fetch('/api/brand/upload-logo', {
        method: 'POST',
        body: formDataToSend,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Logo upload failed');
      }

      const data = await response.json();
      return data.url;
    } catch (err) {
      console.error('Logo upload error:', err);
      return null;
    }
  };

  const submitOnboarding = async (): Promise<boolean> => {
    setError(null);
    setSuccess(false);

    if (!validateCurrentStep()) {
      return false;
    }

    setIsLoading(true);

    try {
      // Upload logo if provided
      let logoUrl = null;
      if (formData.logo_file) {
        logoUrl = await uploadLogo();
      }

      // Create brand profile via API route
      const response = await fetch('/api/brand/onboarding', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: formData.company_name,
          industry: formData.industry,
          phone: formData.phone || null,
          tone: formData.tone,
          dos_donts: formData.dos_donts,
          logo_url: logoUrl,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.error || 'Failed to create brand profile');
        return false;
      }

      setSuccess(true);
      setFormData(INITIAL_STATE);
      setCurrentStep(1);
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
    setCurrentStep(1);
  };

  return {
    formData,
    isLoading,
    error,
    success,
    currentStep,
    updateField,
    submitOnboarding,
    resetForm,
    validateCurrentStep,
    goToNextStep,
    goToPreviousStep,
  };
}
