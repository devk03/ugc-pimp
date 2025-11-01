'use client';

import { useState, useEffect } from 'react';
import { useFormContext } from 'react-hook-form';
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export function BudgetInput() {
  const form = useFormContext();
  const spendValue = form.watch('spend');
  const [pendingSpend, setPendingSpend] = useState<string>(spendValue ?? '');
  const [estimatedViews, setEstimatedViews] = useState<number | null>(null);

  // Sync pendingSpend when form value changes externally
  useEffect(() => {
    setPendingSpend(spendValue ?? '');
  }, [spendValue]);

  const handleConfirm = () => {
    const spendNumber = parseFloat(String(pendingSpend));
    if (isNaN(spendNumber) || spendNumber <= 0) {
      // Trigger validation error on spend if invalid
      form.setValue('spend', String(pendingSpend), { shouldValidate: true, shouldDirty: true });
      form.trigger('spend');
      setEstimatedViews(null);
      return;
    }

    // Save the spend to the form only on confirm
    form.setValue('spend', String(pendingSpend), { shouldValidate: true, shouldDirty: true });
    form.trigger('spend');

    // Mock estimator: random multiplier between 4200 and 4500 inclusive
    const multiplier = Math.floor(4200 + Math.random() * (4500 - 4200 + 1));
    const views = Math.round(spendNumber * multiplier);
    setEstimatedViews(views);
  };

  return (
    <>
      <FormField
        control={form.control}
        name="spend"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Campaign Budget</FormLabel>
            <FormControl>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  placeholder="0.00"
                  step="0.01"
                  name={field.name}
                  value={pendingSpend}
                  onChange={(e) => setPendingSpend(e.target.value)}
                  onBlur={field.onBlur}
                  ref={field.ref}
                />
                <Button type="button" onClick={handleConfirm} className="shrink-0">
                  Confirm
                </Button>
              </div>
            </FormControl>
            <FormDescription>
              Total budget allocated for this campaign
            </FormDescription>
            <FormMessage />
            {estimatedViews !== null && (
              <div className="mt-2 text-sm text-muted-foreground">
                Estimated Views: <span className="font-medium">{estimatedViews.toLocaleString()}</span>
              </div>
            )}
          </FormItem>
        )}
      />
    </>
  );
}
