'use client';

import { ShoppingCart } from 'lucide-react';
import type { CartSummaryCard as CartSummaryCardType } from '@/lib/types';

interface CartSummaryCardProps {
  card: CartSummaryCardType;
  onViewCart?: () => void;
}

export function CartSummaryCard({ card, onViewCart }: CartSummaryCardProps) {
  const subtotal = card.data.subtotalCents / 100;
  const currency = card.data.currency || 'USD';

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <ShoppingCart className="w-5 h-5 text-green-600" />
        <div className="flex-1">
          <p className="text-sm font-medium text-green-900">
            Cart: {card.data.itemCount} {card.data.itemCount === 1 ? 'item' : 'items'} · {currency} ${subtotal.toFixed(2)}
          </p>
        </div>
        {onViewCart && (
          <button
            onClick={onViewCart}
            className="px-3 py-1 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            View cart
          </button>
        )}
      </div>
    </div>
  );
}
