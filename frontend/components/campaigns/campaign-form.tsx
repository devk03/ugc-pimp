'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCampaignForm } from '@/hooks/use-campaign-form';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X, Check, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const formSchema = z.object({
  name: z.string().min(2, 'Campaign name must be at least 2 characters'),
  product: z.string().min(2, 'Product name must be at least 2 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  spend: z.string().refine(
    (val) => {
      const num = parseFloat(val);
      return !isNaN(num) && num > 0;
    },
    'Spend must be a positive number'
  ),
  scheduled_start_date: z.string().optional(),
  scheduled_end_date: z.string().optional(),
});

// Step-specific schemas for validation
const step1Schema = z.object({
  name: z.string().min(2, 'Campaign name must be at least 2 characters'),
  product: z.string().min(2, 'Product name must be at least 2 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
});

const step2Schema = z.object({
  spend: z.string().refine(
    (val) => {
      const num = parseFloat(val);
      return !isNaN(num) && num > 0;
    },
    'Spend must be a positive number'
  ),
  scheduled_start_date: z.string().optional(),
  scheduled_end_date: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

const STEPS = [
  { id: 1, label: 'Campaign Info', description: 'Basic information' },
  { id: 2, label: 'Budget & Schedule', description: 'Budget and dates' },
  { id: 3, label: 'Assets', description: 'Upload assets' },
] as const;

interface CampaignFormProps {
  brandId: string;
  campaign?: {
    id: string;
    name: string;
    product: string | null;
    description: string | null;
    spend: number | null;
    state?: string;
    scheduled_start_date?: string | null;
    scheduled_end_date?: string | null;
  };
}

export function CampaignForm({ brandId, campaign }: CampaignFormProps) {
  const router = useRouter();
  const isEdit = !!campaign;
  const [actionType, setActionType] = useState<'draft' | 'schedule' | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  
  const {
    formData,
    submitCampaignWithData,
    error: hookError,
    isLoading,
    uploadProgress,
    addAssets,
    removeAsset,
    updateField,
  } = useCampaignForm();

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: campaign?.name || '',
      product: campaign?.product || '',
      description: campaign?.description || '',
      spend: campaign?.spend?.toString() || '',
      scheduled_start_date: campaign?.scheduled_start_date ? new Date(campaign.scheduled_start_date).toISOString().split('T')[0] : '',
      scheduled_end_date: campaign?.scheduled_end_date ? new Date(campaign.scheduled_end_date).toISOString().split('T')[0] : '',
    },
  });

  // Update form when campaign prop changes (for edit mode)
  // Use campaign.id to track when we need to reset the form
  useEffect(() => {
    if (campaign?.id) {
      form.reset({
        name: campaign.name || '',
        product: campaign.product || '',
        description: campaign.description || '',
        spend: campaign.spend?.toString() || '',
        scheduled_start_date: campaign.scheduled_start_date ? new Date(campaign.scheduled_start_date).toISOString().split('T')[0] : '',
        scheduled_end_date: campaign.scheduled_end_date ? new Date(campaign.scheduled_end_date).toISOString().split('T')[0] : '',
      });
      // Mark all steps as completed in edit mode
      setCompletedSteps([1, 2, 3]);
      setCurrentStep(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign?.id]); // Only depend on campaign.id, not the whole object or functions

  // Step validation functions
  const validateStep = async (step: number): Promise<boolean> => {
    const formValues = form.getValues();
    
    if (step === 1) {
      const result = step1Schema.safeParse(formValues);
      if (!result.success) {
        form.trigger(['name', 'product', 'description']);
        return false;
      }
      return true;
    }
    
    if (step === 2) {
      const result = step2Schema.safeParse(formValues);
      if (!result.success) {
        form.trigger(['spend', 'scheduled_start_date', 'scheduled_end_date']);
        return false;
      }
      return true;
    }
    
    return true; // Step 3 (Assets) has no required validation
  };

  // Navigation handlers
  const handleNext = async () => {
    const isValid = await validateStep(currentStep);
    if (isValid) {
      setCompletedSteps(prev => [...prev.filter(s => s !== currentStep), currentStep]);
      if (currentStep < STEPS.length) {
        setCurrentStep(currentStep + 1);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const goToStep = (step: number) => {
    // In edit mode, allow free navigation; otherwise require previous steps to be completed
    if (isEdit || completedSteps.includes(step - 1) || step === 1) {
      setCurrentStep(step);
    }
  };

  const handleAssetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      addAssets(files);
    }
  };

  const onSubmit = async (data: FormData, state: 'DRAFT' | 'SCHEDULED' = 'DRAFT') => {
    // Update hook's formData with current form values before submission
    updateField('name', data.name);
    updateField('product', data.product);
    updateField('description', data.description);
    updateField('spend', data.spend);

    const scheduled_start_date = data.scheduled_start_date || undefined;
    const scheduled_end_date = data.scheduled_end_date || undefined;

    // Submit using hook, but pass form data directly
    const success = await submitCampaignWithData(
      brandId,
      {
        name: data.name,
        product: data.product,
        description: data.description,
        spend: data.spend,
      },
      {
        campaignId: campaign?.id,
        state,
        scheduled_start_date,
        scheduled_end_date,
      }
    );

    if (success) {
      router.push(campaign ? `/dashboard/campaigns/${campaign.id}` : '/dashboard');
      router.refresh();
    }
  };

  const handleSaveDraft = async (data: FormData) => {
    setActionType('draft');
    await onSubmit(data, 'DRAFT');
    setActionType(null);
  };

  const handleSchedule = async (data: FormData) => {
    setActionType('schedule');
    await onSubmit(data, 'SCHEDULED');
    setActionType(null);
  };

  // Step Indicator Component
  const StepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {STEPS.map((step, index) => {
        const isCompleted = completedSteps.includes(step.id);
        const isCurrent = currentStep === step.id;
        const isAccessible = isEdit || completedSteps.includes(step.id - 1) || step.id === 1;
        
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <button
                type="button"
                onClick={() => isAccessible && goToStep(step.id)}
                disabled={!isAccessible}
                className={`relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all ${
                  isCurrent
                    ? 'border-purple-600 bg-purple-600 text-white'
                    : isCompleted
                    ? 'border-green-500 bg-green-500 text-white'
                    : isAccessible
                    ? 'border-gray-300 dark:border-gray-700 bg-background hover:border-purple-400'
                    : 'border-gray-200 dark:border-gray-800 bg-gray-100 dark:bg-gray-900 cursor-not-allowed'
                }`}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <span className="text-sm font-semibold">{step.id}</span>
                )}
              </button>
              <div className="mt-2 text-center">
                <p className={`text-xs font-medium ${isCurrent ? 'text-purple-600' : 'text-muted-foreground'}`}>
                  {step.label}
                </p>
                <p className="text-xs text-muted-foreground hidden sm:block">{step.description}</p>
              </div>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={`w-24 h-0.5 mx-4 transition-colors ${
                  completedSteps.includes(step.id) ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-800'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );

  // Step Content Components
  const Step1Content = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Campaign Information</h3>
        <div className="grid gap-6">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Campaign Name</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., Summer Product Launch" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="product"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Product Name</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., New Skincare Line" {...field} />
                </FormControl>
                <FormDescription>
                  What product is this campaign promoting?
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Campaign Description</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Describe your campaign goals, target audience, and any specific requirements for creators..."
                    {...field}
                    rows={5}
                  />
                </FormControl>
                <FormDescription>
                  This helps creators understand your vision
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    </div>
  );

  const Step2Content = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Budget</h3>
        <div className="grid gap-6">
          <FormField
            control={form.control}
            name="spend"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Campaign Budget</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    placeholder="0.00"
                    step="0.01"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Total budget allocated for this campaign
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-lg font-semibold mb-4">Schedule (Optional)</h3>
        <div className="grid gap-6 md:grid-cols-2">
          <FormField
            control={form.control}
            name="scheduled_start_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Date</FormLabel>
                <FormControl>
                  <Input
                    type="date"
                    {...field}
                    value={field.value || ''}
                  />
                </FormControl>
                <FormDescription>
                  When should this campaign start?
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="scheduled_end_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>End Date</FormLabel>
                <FormControl>
                  <Input
                    type="date"
                    {...field}
                    value={field.value || ''}
                  />
                </FormControl>
                <FormDescription>
                  When should this campaign end?
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    </div>
  );

  const Step3Content = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Campaign Assets</h3>
        <div className="space-y-4">
          <FormItem>
            <FormLabel>Upload Creative Assets</FormLabel>
            <FormControl>
              <div className="space-y-4">
                <Input
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  onChange={handleAssetChange}
                  disabled={isLoading}
                />
                <FormDescription>
                  Upload images and videos that creators can use as reference
                </FormDescription>
              </div>
            </FormControl>
          </FormItem>

          {/* Assets List */}
          {formData.assets.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-medium text-sm">
                Uploaded Assets ({formData.assets.length})
              </h4>
              <div className="grid gap-2">
                {formData.assets.map((asset, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted rounded-md"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className="text-sm font-medium truncate">
                        {asset.name}
                      </span>
                      <Badge variant="secondary" className="text-xs whitespace-nowrap">
                        {(asset.size / 1024 / 1024).toFixed(2)} MB
                      </Badge>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeAsset(index)}
                      className="ml-2 p-1 hover:bg-accent rounded"
                      disabled={isLoading}
                    >
                      <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {isLoading && uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Uploading assets...</span>
                <span>{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} />
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="w-full max-w-4xl mx-auto py-8">
      <Card>
        <CardHeader>
          <CardTitle className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            {isEdit ? 'Edit Campaign' : 'Create New Campaign'}
          </CardTitle>
          <CardDescription>
            {isEdit ? 'Update your campaign details and schedule' : 'Set up a new UGC campaign and upload creative assets'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
              {/* Step Indicator */}
              <StepIndicator />

              {/* Step Content */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  {currentStep === 1 && <Step1Content />}
                  {currentStep === 2 && <Step2Content />}
                  {currentStep === 3 && <Step3Content />}
                </motion.div>
              </AnimatePresence>

              {hookError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded dark:bg-red-950 dark:border-red-800 dark:text-red-200">
                  {hookError}
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t">
                <div className="flex gap-4 flex-1">
                  {currentStep > 1 && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleBack}
                      disabled={isLoading}
                      className="flex-1 sm:flex-initial"
                    >
                      Back
                    </Button>
                  )}
                </div>
                <div className="flex gap-4 flex-1 sm:justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={isLoading || actionType === 'schedule'}
                    onClick={form.handleSubmit(handleSaveDraft)}
                    className="flex-1 sm:flex-initial"
                  >
                    {isLoading && actionType === 'draft' 
                      ? `Saving draft... ${uploadProgress}%` 
                      : isEdit ? 'Save as Draft' : 'Save Draft'}
                  </Button>
                  {currentStep < STEPS.length && (
                    <Button
                      type="button"
                      onClick={handleNext}
                      disabled={isLoading}
                      className="flex-1 sm:flex-initial bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
                    >
                      Next
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </Button>
                  )}
                  {currentStep === STEPS.length && (
                    <Button
                      type="button"
                      disabled={isLoading || actionType === 'draft'}
                      onClick={form.handleSubmit(handleSchedule)}
                      className="flex-1 sm:flex-initial bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
                    >
                      {isLoading && actionType === 'schedule'
                        ? `Scheduling... ${uploadProgress}%`
                        : isEdit ? 'Update & Schedule' : 'Schedule Campaign'}
                    </Button>
                  )}
                </div>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
