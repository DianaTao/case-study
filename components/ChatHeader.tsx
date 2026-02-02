'use client';

import Image from 'next/image';
import { RotateCcw, ShoppingCart, Refrigerator } from 'lucide-react';
import { useChatStore } from '@/lib/store';

interface ChatHeaderProps {
  onReset?: () => void;
  onCartClick?: () => void;
}

export function ChatHeader({ onReset, onCartClick }: ChatHeaderProps) {
  const { applianceType, modelNumber, cart } = useChatStore();

  const cartItemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) || 0;

  return (
    <div className="bg-white border-b border-partselect-border px-4 py-3">
      {/* Top Row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center">
            <Image
              src="/Attached_image.png"
              alt="PartSelect"
              width={120}
              height={24}
              priority
            />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-partselect-text-primary">
              PartSelect Assistant
            </h1>
            <p className="text-xs text-partselect-text-secondary">
              Expert help for refrigerator and dishwasher parts only.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Cart */}
          <button
            onClick={onCartClick}
            className="relative p-2 hover:bg-partselect-surface rounded-lg transition-colors"
          >
            <ShoppingCart className="w-5 h-5 text-partselect-text-secondary" />
            {cartItemCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-partselect-accent text-white text-xs rounded-full flex items-center justify-center">
                {cartItemCount}
              </span>
            )}
          </button>

          {/* Reset */}
          <button
            onClick={onReset}
            className="p-2 hover:bg-partselect-surface rounded-lg transition-colors"
            title="Reset conversation"
          >
            <RotateCcw className="w-5 h-5 text-partselect-text-secondary" />
          </button>
        </div>
      </div>

      {/* Context Pills */}
      <div className="flex flex-wrap gap-2">
        <div className="px-3 py-1 bg-partselect-surface border border-partselect-border rounded-full text-sm text-partselect-text-secondary">
          <span className="font-medium">Scope:</span> Refrigerator & Dishwasher Parts
        </div>
        
        {applianceType && (
          <div className="px-3 py-1 bg-blue-50 border border-blue-200 rounded-full text-sm text-partselect-primary flex items-center gap-1">
            <Refrigerator className="w-3 h-3" />
            <span className="capitalize">{applianceType}</span>
          </div>
        )}

        {modelNumber && (
          <div className="px-3 py-1 bg-green-50 border border-green-200 rounded-full text-sm text-partselect-success">
            <span className="font-medium">Model:</span> {modelNumber}
          </div>
        )}
      </div>
    </div>
  );
}
