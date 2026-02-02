'use client';

import { X, ExternalLink, Trash2 } from 'lucide-react';
import { formatPrice } from '@/lib/utils';
import type { Cart } from '@/lib/types';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  cart: Cart | null;
  onUpdateQuantity?: (partselectNumber: string, quantity: number) => void;
}

export function CartDrawer({ isOpen, onClose, cart, onUpdateQuantity }: CartDrawerProps) {
  if (!isOpen) return null;

  const itemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) || 0;

  // Backend returns snake_case (price_cents); frontend Part type uses camelCase (priceCents).
  // Be tolerant and handle both to avoid showing "Price unavailable" when data exists.
  const hasUnknownPrice = Boolean(
    cart?.items.some((item) => {
      const part = item.part;
      if (!part) return true;
      const priceCents =
        (part as any).priceCents ?? (part as any).price_cents ?? null;
      return priceCents === null || priceCents === undefined;
    })
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-partselect-border">
          <h2 className="text-xl font-semibold text-partselect-text-primary">
            Your Cart ({itemCount})
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-partselect-surface rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto p-4">
          {!cart || cart.items.length === 0 ? (
            <div className="text-center py-12 text-partselect-text-secondary">
              <p>Your cart is empty</p>
            </div>
          ) : (
            <div className="space-y-4">
              {cart.items.map((item) => (
                <div
                  key={item.partselectNumber}
                  className="border border-partselect-border rounded-lg p-3"
                >
                  <div className="flex gap-3">
                    {item.part?.imageUrl && (
                      <img
                        src={item.part.imageUrl}
                        alt={item.part.name}
                        className="w-16 h-16 object-contain rounded"
                      />
                    )}
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-partselect-text-primary line-clamp-2">
                        {item.part?.name || item.partselectNumber}
                      </h3>
                      <p className="text-sm text-partselect-text-secondary font-mono">
                        {item.partselectNumber}
                      </p>
                      {item.part && (
                        <p className="text-lg font-semibold text-partselect-primary mt-1">
                          {(() => {
                            const part: any = item.part;
                            const unitPriceCents =
                              part.priceCents ?? part.price_cents ?? null;
                            return unitPriceCents !== null &&
                              unitPriceCents !== undefined
                              ? formatPrice(unitPriceCents * item.quantity)
                              : 'Price unavailable';
                          })()}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() =>
                          onUpdateQuantity?.(
                            item.partselectNumber,
                            Math.max(1, item.quantity - 1)
                          )
                        }
                        className="w-8 h-8 border border-partselect-border rounded hover:bg-partselect-surface"
                      >
                        -
                      </button>
                      <span className="w-8 text-center">{item.quantity}</span>
                      <button
                        onClick={() =>
                          onUpdateQuantity?.(item.partselectNumber, item.quantity + 1)
                        }
                        className="w-8 h-8 border border-partselect-border rounded hover:bg-partselect-surface"
                      >
                        +
                      </button>
                    </div>

                    <button
                      onClick={() => onUpdateQuantity?.(item.partselectNumber, 0)}
                      className="p-2 text-partselect-accent hover:bg-red-50 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {cart && cart.items.length > 0 && (
          <div className="border-t border-partselect-border p-4 space-y-3">
            <div className="flex items-center justify-between text-lg font-semibold">
              <span>Total:</span>
              <span className="text-partselect-primary">
                {hasUnknownPrice ? 'Total unavailable' : formatPrice(cart.totalCents)}
              </span>
            </div>

            <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-partselect-primary text-white rounded-lg hover:bg-blue-600 transition-colors">
              Proceed to Checkout
              <ExternalLink className="w-4 h-4" />
            </button>

            <p className="text-xs text-center text-partselect-text-secondary">
              Checkout on PartSelect.com
            </p>
          </div>
        )}
      </div>
    </>
  );
}
