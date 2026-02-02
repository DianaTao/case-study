'use client';

import { AlertCircle } from 'lucide-react';
import type { OutOfScopeCard as OutOfScopeCardType } from '@/lib/types';

interface OutOfScopeCardProps {
  card: OutOfScopeCardType;
  onActionClick?: (action: string) => void;
}

export function OutOfScopeCard({ card, onActionClick }: OutOfScopeCardProps) {
  const { data } = card;

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-6 h-6 text-orange-600 flex-shrink-0 mt-0.5" />
        
        <div className="flex-1">
          <h3 className="font-semibold text-orange-900 mb-2">Out of Scope</h3>
          <p className="text-orange-800 mb-4">{data.message}</p>

          {/* Example Queries */}
          {data.exampleQueries && data.exampleQueries.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-orange-700 mb-2">Example questions I can help with:</p>
              <ul className="space-y-1">
                {data.exampleQueries.map((query, index) => (
                  <li key={index} className="text-sm text-orange-800">
                    • {query}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Actions */}
          {data.suggestedActions && data.suggestedActions.length > 0 && (
            <div>
              <p className="text-sm text-orange-700 mb-2">Try asking about:</p>
              <div className="flex flex-wrap gap-2">
                {data.suggestedActions.map((action, index) => (
                  <button
                    key={index}
                    onClick={() => onActionClick?.(action)}
                    className="px-3 py-1 bg-white border border-orange-300 text-orange-700 rounded-full text-sm hover:bg-orange-100 transition-colors"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
