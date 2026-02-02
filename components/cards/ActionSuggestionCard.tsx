'use client';

import { ArrowRight } from 'lucide-react';
import type { ActionSuggestionCard as ActionSuggestionCardType } from '@/lib/types';

interface ActionSuggestionCardProps {
  card: ActionSuggestionCardType;
  onAction?: (action: string) => void;
}

export function ActionSuggestionCard({ card, onAction }: ActionSuggestionCardProps) {
  return (
    <div className="flex justify-center py-2">
      <button
        onClick={() => onAction?.(card.data.action)}
        className="flex items-center gap-2 px-4 py-2 text-sm text-partselect-text-secondary hover:text-partselect-primary border border-partselect-border rounded-lg hover:bg-partselect-surface transition-colors"
      >
        <span>{card.data.label}</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
