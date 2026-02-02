'use client';

import { useState } from 'react';
import { ShoppingCart, Video, FileText, Star } from 'lucide-react';
import { formatPrice } from '@/lib/utils';
import type { ProductCard as ProductCardType } from '@/lib/types';

interface ProductCardProps {
  card: ProductCardType;
  onAddToCart?: (partselectNumber: string) => void;
  onRefreshPrice?: (partselectNumber: string) => void;
}

export function ProductCard({ card, onAddToCart, onRefreshPrice }: ProductCardProps) {
  const { data } = card;
  const [isAdding, setIsAdding] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const priceText = data.price !== null && data.price !== undefined
    ? formatPrice(data.price * 100)
    : formatPrice(undefined);
  const inStockLabel =
    data.inStock === true ? 'In Stock' :
    data.inStock === false ? 'Out of Stock' :
    'Availability unknown';
  const canAddToCart = data.inStock === true && data.price !== null && data.price !== undefined;
  const canRefreshPrice =
    data.price === null ||
    data.price === undefined ||
    data.inStock === null ||
    data.inStock === undefined;

  const handleAddToCart = async () => {
    setIsAdding(true);
    try {
      await onAddToCart?.(data.partselectNumber);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRefreshPrice = async () => {
    if (!onRefreshPrice) return;
    setIsRefreshing(true);
    try {
      await onRefreshPrice(data.partselectNumber);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="bg-white border border-partselect-border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex gap-4">
        {data.imageUrl && (
          <div className="flex-shrink-0">
            <img
              src={data.imageUrl}
              alt={data.title}
              className="w-24 h-24 object-contain rounded"
            />
          </div>
        )}
        
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-partselect-text-primary line-clamp-2">
            {data.title}
          </h3>
          
          {/* Rating */}
          {data.rating && (
            <div className="flex items-center gap-1 mt-1">
              <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
              <span className="text-sm font-medium">{data.rating}</span>
              <span className="text-sm text-partselect-text-secondary">
                ({data.reviewCount} reviews)
              </span>
            </div>
          )}

          {/* Part Numbers */}
          <div className="mt-2 space-y-1">
            <div className="text-sm">
              <span className="text-partselect-text-secondary">PartSelect #:</span>{' '}
              <span className="font-mono font-medium">{data.partselectNumber}</span>
            </div>
            {data.manufacturerPartNumber && (
              <div className="text-sm">
                <span className="text-partselect-text-secondary">Mfr #:</span>{' '}
                <span className="font-mono">{data.manufacturerPartNumber}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Price and Stock */}
      <div className="mt-4 flex items-center justify-between">
        <div>
          <div className="text-2xl font-bold text-partselect-primary">
            {priceText}
          </div>
          {/* Stock status pill, aligned with PartSelect-style badge */}
          <div className="mt-1">
            <span
              className={[
                'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold',
                data.inStock === true
                  ? 'bg-green-100 text-partselect-success border border-green-200'
                  : data.inStock === false
                  ? 'bg-red-100 text-partselect-accent border border-red-200'
                  : 'bg-gray-100 text-partselect-text-secondary border border-gray-200',
              ].join(' ')}
            >
              {inStockLabel}
            </span>
          </div>
          {/* GUARDRAIL: Provenance label for price/stock */}
          {data.provenance && (
            <div className="text-xs text-partselect-text-secondary mt-1 italic">
              {data.provenance}
            </div>
          )}
        </div>

        <button
          onClick={handleAddToCart}
          disabled={!canAddToCart || isAdding}
          className="flex items-center gap-2 px-4 py-2 bg-[rgb(205,169,84)] text-white rounded-lg hover:bg-[rgb(174,143,71)] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          <ShoppingCart className="w-4 h-4" />
          {isAdding ? 'Adding...' : 'Add to Cart'}
        </button>
      </div>

      {onRefreshPrice && canRefreshPrice && (
        <div className="mt-2">
          <button
            onClick={handleRefreshPrice}
            disabled={isRefreshing}
            className="text-sm text-partselect-primary hover:underline disabled:text-partselect-text-secondary"
          >
            {isRefreshing ? 'Refreshing price...' : 'Refresh price/stock'}
          </button>
        </div>
      )}

      {data.productUrl && (
        <div className="mt-3">
          <a
            href={data.productUrl}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-partselect-primary hover:underline"
          >
            View on PartSelect
          </a>
        </div>
      )}

      {/* Install Resources */}
      {(data.install?.hasVideos || data.install?.hasInstructions) && (
        <div className="mt-3 pt-3 border-t border-partselect-border">
          <div className="flex gap-3">
            {data.install.hasVideos && (
              <div className="flex items-center gap-1 text-sm text-partselect-primary">
                <Video className="w-4 h-4" />
                <span>Videos available</span>
              </div>
            )}
            {data.install.hasInstructions && (
              <div className="flex items-center gap-1 text-sm text-partselect-primary">
                <FileText className="w-4 h-4" />
                <span>Instructions available</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
