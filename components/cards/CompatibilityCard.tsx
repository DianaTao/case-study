'use client';

import { CheckCircle, XCircle, AlertCircle, ExternalLink } from 'lucide-react';
import type { CompatibilityCard as CompatibilityCardType } from '@/lib/types';

interface CompatibilityCardProps {
  card: CompatibilityCardType;
}

export function CompatibilityCard({ card }: CompatibilityCardProps) {
  const { data } = card;

  const statusConfig = {
    fits: {
      icon: CheckCircle,
      color: 'text-partselect-success',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      label: 'Compatible',
    },
    no_fit: {
      icon: XCircle,
      color: 'text-partselect-accent',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      label: 'Not Compatible',
    },
    // Some backends use "does_not_fit" instead of "no_fit"
    does_not_fit: {
      icon: XCircle,
      color: 'text-partselect-accent',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      label: 'Not Compatible',
    },
    need_info: {
      icon: AlertCircle,
      color: 'text-partselect-warning',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      label: 'Need More Info',
    },
  };

  const config = statusConfig[data.status] ?? statusConfig.need_info;
  const Icon = config.icon;

  return (
    <div className={`border ${config.borderColor} ${config.bgColor} rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-6 h-6 ${config.color} flex-shrink-0 mt-0.5`} />
        
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className={`font-semibold ${config.color}`}>{config.label}</h3>
          </div>

          <p className="text-partselect-text-primary mb-3">{data.reason}</p>

          {/* Part and Model Info */}
          <div className="space-y-1 text-sm">
            <div>
              <span className="text-partselect-text-secondary">Part:</span>{' '}
              <span className="font-mono font-medium">{data.partselectNumber}</span>
            </div>
            {data.modelNumber && (
              <div>
                <span className="text-partselect-text-secondary">Model:</span>{' '}
                <span className="font-mono font-medium">{data.modelNumber}</span>
              </div>
            )}
          </div>

          {/* Model Page Link - Show prominently if available */}
          {data.modelPageUrl && (
            <div className="mt-3">
              <a
                href={data.modelPageUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-partselect-primary text-white rounded-lg hover:bg-partselect-primary/90 transition-colors text-sm font-medium"
              >
                View all parts for {data.modelNumber || 'this model'}
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          )}

          {/* Evidence */}
          {data.evidence && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <details className="text-sm">
                <summary className="cursor-pointer text-partselect-primary hover:underline">
                  Why?
                </summary>
                <div className="mt-2 text-partselect-text-secondary">
                  {data.evidence.snippet && (
                    <p className="mb-2">{data.evidence.snippet}</p>
                  )}
                  {data.evidence.url && (
                    <a
                      href={data.evidence.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-partselect-primary hover:underline"
                    >
                      View source
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
