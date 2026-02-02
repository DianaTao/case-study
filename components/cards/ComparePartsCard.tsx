'use client';

import type { ComparePartsCard as ComparePartsCardType } from '@/lib/types';

interface ComparePartsCardProps {
  card: ComparePartsCardType;
  onPartClick?: (partselectNumber: string) => void;
}

export function ComparePartsCard({ card, onPartClick }: ComparePartsCardProps) {
  const parts = card.data.parts;

  if (parts.length < 2) return null;

  return (
    <div className="bg-white border border-partselect-border rounded-lg p-4 shadow-sm">
      <h3 className="font-semibold text-partselect-text-primary mb-4">
        Compare Parts
      </h3>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-partselect-border">
              <th className="text-left py-2 px-3 font-semibold text-partselect-text-secondary">Part</th>
              <th className="text-left py-2 px-3 font-semibold text-partselect-text-secondary">Likelihood</th>
              <th className="text-left py-2 px-3 font-semibold text-partselect-text-secondary">Price</th>
              <th className="text-left py-2 px-3 font-semibold text-partselect-text-secondary">Difficulty</th>
            </tr>
          </thead>
          <tbody>
            {parts.map((part, index) => (
              <tr
                key={part.partselectNumber}
                className={`border-b border-partselect-border hover:bg-partselect-surface cursor-pointer ${
                  index === parts.length - 1 ? 'border-b-0' : ''
                }`}
                onClick={() => onPartClick?.(part.partselectNumber)}
              >
                <td className="py-3 px-3">
                  <div>
                    <div className="font-medium text-partselect-text-primary">{part.name}</div>
                    <div className="text-xs text-partselect-text-secondary">{part.partselectNumber}</div>
                  </div>
                </td>
                <td className="py-3 px-3">
                  {part.likelihood && (
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        part.likelihood === 'high'
                          ? 'bg-green-100 text-green-800'
                          : part.likelihood === 'medium'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {part.likelihood}
                    </span>
                  )}
                </td>
                <td className="py-3 px-3">
                  {part.priceCents !== undefined ? (
                    <span className="font-medium">${(part.priceCents / 100).toFixed(2)}</span>
                  ) : (
                    <span className="text-partselect-text-secondary">—</span>
                  )}
                </td>
                <td className="py-3 px-3">
                  {part.difficulty && (
                    <span className="capitalize text-partselect-text-secondary">{part.difficulty}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
