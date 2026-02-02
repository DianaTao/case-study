'use client';

import { Search, CheckCircle, Wrench, Package, HelpCircle } from 'lucide-react';

interface QuickActionsProps {
  onActionClick: (action: string) => void;
}

const actions = [
  {
    icon: Search,
    label: 'Find a part by problem',
    query: 'Find a part by problem (e.g. "fridge not cooling")',
  },
  {
    icon: CheckCircle,
    label: 'Check if a part fits my model',
    query: 'Check if a part fits my model',
  },
  {
    icon: Wrench,
    label: 'Show me how to install a part',
    query: 'Show me how to install a part',
  },
  {
    icon: HelpCircle,
    label: 'Help with a dishwasher not draining',
    query: 'Help with a dishwasher not draining',
  },
];

export function QuickActions({ onActionClick }: QuickActionsProps) {
  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-partselect-text-secondary mb-3">
        Quick Actions
      </h3>
      
      <div className="grid grid-cols-2 gap-2">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => onActionClick(action.query)}
            className="flex flex-col items-center gap-2 p-3 border border-partselect-border rounded-lg hover:bg-partselect-surface hover:border-partselect-primary transition-colors"
          >
            <action.icon className="w-6 h-6 text-partselect-primary" />
            <span className="text-sm text-center text-partselect-text-primary">
              {action.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
