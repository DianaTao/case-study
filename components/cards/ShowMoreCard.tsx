'use client';

import { ChevronDown } from 'lucide-react';
import type { ShowMoreCard as ShowMoreCardType } from '@/lib/types';

interface ShowMoreCardProps {
  card: ShowMoreCardType;
  onLoadMore?: () => void;
}

export function ShowMoreCard({ card, onLoadMore }: ShowMoreCardProps) {
  const { totalAvailable, shown } = card.data;
  const remaining = totalAvailable - shown;

  return (
    <div className="flex justify-center py-2">
      <button
        onClick={onLoadMore}
        className="flex items-center gap-2 px-4 py-2 text-sm text-partselect-primary hover:text-partselect-primary/80 border border-partselect-border rounded-lg hover:bg-partselect-surface transition-colors"
      >
        <span>Show {remaining} more {remaining === 1 ? 'part' : 'parts'}</span>
        <ChevronDown className="w-4 h-4" />
      </button>
    </div>
  );
}
