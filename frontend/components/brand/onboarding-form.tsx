'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useBrandOnboarding } from '@/hooks/use-brand-onboarding';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ChevronRight, ChevronLeft } from 'lucide-react';

const industries = [
  'E-commerce',
  'Technology',
  'Fashion',
  'Beauty',
  'Food & Beverage',
  'Health & Wellness',
  'Home & Lifestyle',
  'Travel',
  'Finance',
  'Education',
  'Entertainment',
  'Sports',
  'Automotive',
  'Real Estate',
  'Other',
];

interface OnboardingFormProps {
  userEmail: string;
}

export function OnboardingForm({ userEmail }: OnboardingFormProps) {
  const router = useRouter();
  const {
    formData,
    currentStep,
    isLoading,
    error,
    updateField,
    goToNextStep,
    goToPreviousStep,
    submitOnboarding,
  } = useBrandOnboarding();

  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      updateField('logo_file', file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    const success = await submitOnboarding();
    if (success) {
      router.push('/dashboard');
    }
  };

  const handleNextStep = () => {
    goToNextStep();
  };

  const progressPercent = (currentStep / 3) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto py-8">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex gap-2 mb-4">
          {[1, 2, 3].map((step) => (
            <div
              key={step}
              className={`flex-1 h-1 rounded-full transition-colors ${
                step <= currentStep ? 'bg-blue-500' : 'bg-muted'
              }`}
            />
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          Step {currentStep} of 3
        </p>
      </div>

      {/* Step 1: Basic Information */}
      {currentStep === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Tell us about your brand
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="company_name">Company Name *</Label>
              <Input
                id="company_name"
                placeholder="Your company name"
                value={formData.company_name}
                onChange={(e) => updateField('company_name', e.target.value)}
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry">Industry *</Label>
              <Select
                value={formData.industry}
                onValueChange={(value) => updateField('industry', value)}
                disabled={isLoading}
              >
                <SelectTrigger id="industry">
                  <SelectValue placeholder="Select your industry" />
                </SelectTrigger>
                <SelectContent>
                  {industries.map((industry) => (
                    <SelectItem key={industry} value={industry}>
                      {industry}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="logo">Logo</Label>
              <Input
                id="logo"
                type="file"
                accept="image/*"
                onChange={handleLogoChange}
                disabled={isLoading}
              />
              {logoPreview && (
                <div className="relative w-32 h-32 mt-4">
                  <img
                    src={logoPreview}
                    alt="Logo preview"
                    className="w-full h-full object-cover rounded-md border"
                  />
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <Button
                onClick={handleNextStep}
                disabled={isLoading}
                className="gap-2"
              >
                Next <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Contact Details */}
      {currentStep === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Contact Details</CardTitle>
            <CardDescription>
              How can creators reach you?
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={userEmail}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">
                Email from your account
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+1 (555) 000-0000"
                value={formData.phone}
                onChange={(e) => updateField('phone', e.target.value)}
                disabled={isLoading}
              />
              <p className="text-xs text-muted-foreground">
                Optional - leave blank if you prefer
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-between gap-3 pt-4">
              <Button
                variant="outline"
                onClick={goToPreviousStep}
                disabled={isLoading}
                className="gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </Button>
              <Button
                onClick={handleNextStep}
                disabled={isLoading}
                className="gap-2"
              >
                Next <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Brand Guidelines */}
      {currentStep === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Brand Guidelines</CardTitle>
            <CardDescription>
              Guide creators on how to represent your brand
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="tone">Tone & Voice *</Label>
              <Textarea
                id="tone"
                placeholder="Describe your brand's tone and voice (e.g., professional, friendly, creative, etc.)"
                value={formData.tone}
                onChange={(e) => updateField('tone', e.target.value)}
                disabled={isLoading}
                rows={4}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dos_donts">Do's & Don'ts *</Label>
              <Textarea
                id="dos_donts"
                placeholder="List specific things creators should do and avoid (e.g., 'Do: highlight product features, Don't: use competitors' products')"
                value={formData.dos_donts}
                onChange={(e) => updateField('dos_donts', e.target.value)}
                disabled={isLoading}
                rows={4}
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-between gap-3 pt-4">
              <Button
                variant="outline"
                onClick={goToPreviousStep}
                disabled={isLoading}
                className="gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={isLoading}
              >
                {isLoading ? 'Creating your brand profile...' : 'Complete Onboarding'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
