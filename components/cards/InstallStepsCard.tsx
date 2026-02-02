'use client';

import { useState } from 'react';
import { CheckCircle, AlertTriangle, Video, FileText, ExternalLink, Clock, Wrench, ChevronDown, ChevronUp } from 'lucide-react';
import type { InstallStepsCard as InstallStepsCardType } from '@/lib/types';

interface InstallStepsCardProps {
  card: InstallStepsCardType;
}

export function InstallStepsCard({ card }: InstallStepsCardProps) {
  const { data } = card;
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white border border-partselect-border rounded-lg p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-partselect-text-primary mb-4">
        Installation Steps for {data.partselectNumber}
      </h3>

      {/* Summary - Always visible */}
      {data.summary && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">{data.summary}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="flex flex-wrap gap-4 mb-4 text-sm text-partselect-text-secondary">
        {data.difficulty && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Difficulty:</span>
            <span className="capitalize">{data.difficulty}</span>
          </div>
        )}
        {data.estimatedTimeMinutes && (
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>~{data.estimatedTimeMinutes} min</span>
          </div>
        )}
        {data.tools && data.tools.length > 0 && (
          <div className="flex items-center gap-1">
            <Wrench className="w-4 h-4" />
            <span>{data.tools.join(', ')}</span>
          </div>
        )}
      </div>

      {/* Safety Notes */}
      {data.safetyNotes && data.safetyNotes.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <h4 className="font-semibold text-yellow-900">Safety Notes</h4>
          </div>
          <ul className="list-disc list-inside space-y-1 text-sm text-yellow-800">
            {data.safetyNotes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Expandable Steps */}
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-partselect-primary hover:text-partselect-primary/80 mb-3 transition-colors"
        >
          <span className="font-medium">
            {isExpanded ? 'Hide' : 'Show'} detailed steps ({data.steps.length})
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {isExpanded && (
          <div className="space-y-4 mb-4">
            {data.steps.map((step) => (
              <div key={step.stepNumber} className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-partselect-primary text-white flex items-center justify-center font-semibold">
                  {step.stepNumber}
                </div>
                
                <div className="flex-1">
                  <p className="text-partselect-text-primary mb-1">{step.instruction}</p>
                  
                  {step.safetyNote && (
                    <div className="flex items-start gap-2 mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                      <AlertTriangle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-yellow-800">{step.safetyNote}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Resources */}
      {data.links && data.links.length > 0 && (
        <div className="pt-4 border-t border-partselect-border">
          <h4 className="text-sm font-semibold text-partselect-text-primary mb-2">
            Additional Resources
          </h4>
          <div className="space-y-2">
            {data.links.map((link, index) => (
              <a
                key={index}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-partselect-primary hover:underline"
              >
                {link.type === 'video' ? (
                  <Video className="w-4 h-4" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
                <span>{link.label}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
