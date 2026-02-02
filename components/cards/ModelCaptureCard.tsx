'use client';

import { useState } from 'react';
import { HelpCircle, X } from 'lucide-react';
import type { ModelCaptureCard as ModelCaptureCardType } from '@/lib/types';

interface ModelCaptureCardProps {
  card: ModelCaptureCardType;
  onModelSubmit?: (modelNumber: string) => void;
  onSkip?: () => void;
}

export function ModelCaptureCard({ card, onModelSubmit, onSkip }: ModelCaptureCardProps) {
  const [modelNumber, setModelNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelNumber.trim()) return;
    
    setIsSubmitting(true);
    try {
      await onModelSubmit?.(modelNumber.trim().toUpperCase());
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white border border-partselect-border rounded-lg p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <HelpCircle className="w-5 h-5 text-partselect-primary flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-partselect-text-primary mb-1">
            {card.data.title}
          </h3>
          <p className="text-sm text-partselect-text-secondary mb-4">
            {card.data.body}
          </p>
          
          <form onSubmit={handleSubmit} className="space-y-3">
            <input
              type="text"
              value={modelNumber}
              onChange={(e) => setModelNumber(e.target.value)}
              placeholder="e.g., WDT780SAEM1"
              className="w-full px-3 py-2 border border-partselect-border rounded-lg focus:outline-none focus:ring-2 focus:ring-partselect-primary"
              disabled={isSubmitting}
            />
            
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={!modelNumber.trim() || isSubmitting}
                className="flex-1 px-4 py-2 bg-partselect-primary text-white rounded-lg hover:bg-partselect-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? 'Submitting...' : 'Submit'}
              </button>
              
              {card.data.canSkip && (
                <button
                  type="button"
                  onClick={onSkip}
                  className="px-4 py-2 border border-partselect-border text-partselect-text-secondary rounded-lg hover:bg-partselect-surface transition-colors"
                >
                  Skip
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
