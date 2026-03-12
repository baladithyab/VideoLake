/**
 * WizardLayout - Layout for multi-step wizard flows
 */

import React from 'react';
import type { ReactNode } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressTracker } from '@/components/molecules/ProgressTracker';
import type { ProgressStep } from '@/components/molecules/ProgressTracker';
import { Button } from '@/components/ui/button';

interface WizardLayoutProps {
  children: ReactNode;
  steps: ProgressStep[];
  currentStep: number;
  onStepChange?: (stepIndex: number) => void;
  onNext?: () => void;
  onBack?: () => void;
  onCancel?: () => void;
  onComplete?: () => void;
  nextLabel?: string;
  backLabel?: string;
  completeLabel?: string;
  nextDisabled?: boolean;
  backDisabled?: boolean;
  loading?: boolean;
  className?: string;
}

export function WizardLayout({
  children,
  steps,
  currentStep,
  onStepChange,
  onNext,
  onBack,
  onCancel,
  onComplete,
  nextLabel = 'Next',
  backLabel = 'Back',
  completeLabel = 'Complete',
  nextDisabled = false,
  backDisabled = false,
  loading = false,
  className,
}: WizardLayoutProps) {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Progress header */}
      <div className="bg-white border-b border-gray-200 px-6 py-8">
        <div className="max-w-5xl mx-auto">
          <ProgressTracker
            steps={steps}
            orientation="horizontal"
            onStepClick={onStepChange ? (_, index) => onStepChange(index) : undefined}
          />
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-5xl mx-auto px-6 py-8">
          {/* Current step info */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">
              {steps[currentStep]?.title}
            </h2>
            {steps[currentStep]?.description && (
              <p className="mt-2 text-gray-600">
                {steps[currentStep].description}
              </p>
            )}
          </div>

          {/* Step content */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            {children}
          </div>
        </div>
      </div>

      {/* Navigation footer */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          {/* Left side - Cancel */}
          <div>
            {onCancel && (
              <Button
                variant="ghost"
                onClick={onCancel}
                disabled={loading}
              >
                Cancel
              </Button>
            )}
          </div>

          {/* Right side - Navigation */}
          <div className="flex items-center gap-3">
            {/* Back button */}
            {!isFirstStep && onBack && (
              <Button
                variant="outline"
                onClick={onBack}
                disabled={backDisabled || loading}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                {backLabel}
              </Button>
            )}

            {/* Next/Complete button */}
            {isLastStep ? (
              onComplete && (
                <Button
                  onClick={onComplete}
                  disabled={nextDisabled || loading}
                  className="min-w-[120px]"
                >
                  {loading ? (
                    <>
                      <span className="animate-spin mr-2">⏳</span>
                      Processing...
                    </>
                  ) : (
                    completeLabel
                  )}
                </Button>
              )
            ) : (
              onNext && (
                <Button
                  onClick={onNext}
                  disabled={nextDisabled || loading}
                >
                  {nextLabel}
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact wizard layout for dialogs/modals
 */
export function CompactWizardLayout({
  children,
  steps,
  currentStep,
  onNext,
  onBack,
  onComplete,
  nextDisabled = false,
  loading = false,
}: Omit<WizardLayoutProps, 'onStepChange' | 'onCancel' | 'className'>) {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="flex flex-col">
      {/* Compact progress */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">
            Step {currentStep + 1} of {steps.length}
          </span>
          <span className="text-gray-500">
            {steps[currentStep]?.title}
          </span>
        </div>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4">
        {children}
      </div>

      {/* Footer navigation */}
      <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={onBack}
          disabled={isFirstStep || loading}
          size="sm"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back
        </Button>

        <Button
          onClick={isLastStep ? onComplete : onNext}
          disabled={nextDisabled || loading}
          size="sm"
        >
          {isLastStep ? 'Complete' : 'Next'}
          {!isLastStep && <ArrowRight className="w-4 h-4 ml-1" />}
        </Button>
      </div>
    </div>
  );
}
