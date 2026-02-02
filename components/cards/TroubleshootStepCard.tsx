'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import type { TroubleshootStepCard as TroubleshootStepCardType } from '@/lib/types';

interface TroubleshootStepCardProps {
  card: TroubleshootStepCardType;
  onAnswer?: (flowId: string, answer: string) => void;
  onExitFlow?: (flowId: string) => void;
}

export function TroubleshootStepCard({ card, onAnswer, onExitFlow }: TroubleshootStepCardProps) {
  const { data } = card;
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  const handleSubmit = () => {
    if (selectedOption) {
      onAnswer?.(data.flowId, selectedOption);
    }
  };

  const handleExit = () => {
    onExitFlow?.(data.flowId);
  };

  return (
    <div className="bg-white border border-partselect-border rounded-lg p-4 shadow-sm">
      {/* Breadcrumb and Exit */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm text-partselect-text-secondary">
          {data.flowName && (
            <>
              <span className="font-medium">{data.flowName}</span>
              <span>·</span>
            </>
          )}
          <span>Step {data.stepNumber} of {data.totalSteps}</span>
        </div>
        {(data.canExit !== false) && (
          <button
            onClick={handleExit}
            className="text-xs text-partselect-text-secondary hover:text-partselect-primary transition-colors"
          >
            Exit flow
          </button>
        )}
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-partselect-primary rounded-full h-2 transition-all"
            style={{ width: `${(data.stepNumber / data.totalSteps) * 100}%` }}
          />
        </div>
      </div>

      {/* Question */}
      <h3 className="text-lg font-semibold text-partselect-text-primary mb-4">
        {data.question}
      </h3>

      {/* Options */}
      <div className="space-y-2 mb-4">
        {data.options.map((option) => (
          <button
            key={option.value}
            onClick={() => setSelectedOption(option.value)}
            className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
              selectedOption === option.value
                ? 'border-partselect-primary bg-blue-50'
                : 'border-partselect-border hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{option.label}</span>
              {selectedOption === option.value && (
                <div className="w-5 h-5 rounded-full bg-partselect-primary flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-white" />
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!selectedOption}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-partselect-primary text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        Continue
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
