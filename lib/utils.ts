import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatPrice(cents?: number | null): string {
  if (cents === null || cents === undefined) {
    return 'Price unavailable';
  }
  return `$${(cents / 100).toFixed(2)}`;
}

export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function extractModelNumber(text: string): string | null {
  // Common model number patterns
  const patterns = [
    /\b([A-Z]{2,4}\d{3,}[A-Z0-9]*)\b/g, // e.g., WDT780SAEM1
    /\bmodel[:\s]+([A-Z0-9\-]+)/gi,
    /\b(\d{3,}[A-Z]{1,3}\d*)\b/g,
  ];

  for (const pattern of patterns) {
    const matches = text.match(pattern);
    if (matches && matches.length > 0) {
      return matches[0].replace(/^model[:\s]+/gi, '').trim();
    }
  }

  return null;
}

export function extractPartNumber(text: string): string | null {
  // PartSelect numbers typically start with PS
  const psPattern = /\bPS\d{6,10}\b/gi;
  const matches = text.match(psPattern);
  
  if (matches && matches.length > 0) {
    return matches[0];
  }

  return null;
}

export function normalizeModelNumber(modelNumber: string): string {
  return modelNumber.toUpperCase().trim().replace(/[\s\-]/g, '');
}

export function generateSessionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  // Fallback UUID v4 (RFC4122-ish) without external deps
  const hex = [...Array(256).keys()].map((i) => i.toString(16).padStart(2, '0'));
  const r = globalThis.crypto.getRandomValues(new Uint8Array(16));
  r[6] = (r[6] & 0x0f) | 0x40;
  r[8] = (r[8] & 0x3f) | 0x80;
  return (
    hex[r[0]] + hex[r[1]] + hex[r[2]] + hex[r[3]] + '-' +
    hex[r[4]] + hex[r[5]] + '-' +
    hex[r[6]] + hex[r[7]] + '-' +
    hex[r[8]] + hex[r[9]] + '-' +
    hex[r[10]] + hex[r[11]] + hex[r[12]] + hex[r[13]] + hex[r[14]] + hex[r[15]]
  );
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '_')
    .replace(/^-+|-+$/g, '');
}

// Intent classification helpers
export function detectIntent(message: string): {
  intent: string;
  confidence: number;
  entities: Record<string, any>;
} {
  const lowerMessage = message.toLowerCase();
  const entities: Record<string, any> = {};

  // Extract entities
  const modelNumber = extractModelNumber(message);
  const partNumber = extractPartNumber(message);

  if (modelNumber) entities.modelNumber = modelNumber;
  if (partNumber) entities.partNumber = partNumber;

  // Intent patterns
  const intentPatterns = [
    {
      intent: 'compatibility_check',
      patterns: [
        /\b(compatible|compatibility|fit|fits|work with)\b/i,
        /\b(does.*fit|will.*fit|can.*use)\b/i,
      ],
      confidence: 0.9,
    },
    {
      intent: 'part_lookup',
      patterns: [
        /\b(PS\d{6,10})\b/i,
        /\b(part number|part #)\b/i,
        /\b(need|looking for|find).*part\b/i,
      ],
      confidence: 0.85,
    },
    {
      intent: 'install_help',
      patterns: [
        /\b(install|installation|replace|replacement)\b/i,
        /\bhow (do|to).*install\b/i,
        /\bsteps.*install\b/i,
      ],
      confidence: 0.8,
    },
    {
      intent: 'troubleshoot',
      patterns: [
        /\b(not working|broken|problem|issue|fix)\b/i,
        /\b(ice maker|water dispenser|door seal|drain)\b/i,
        /\bhow (do|to).*(fix|repair)\b/i,
      ],
      confidence: 0.85,
    },
    {
      intent: 'cart_action',
      patterns: [
        /\b(add to cart|buy|purchase|order|checkout)\b/i,
        /\b(cart|shopping)\b/i,
      ],
      confidence: 0.9,
    },
    {
      intent: 'order_support',
      patterns: [
        /\b(order|shipping|delivery|track)\b/i,
        /\bwhere.*order\b/i,
      ],
      confidence: 0.85,
    },
    {
      intent: 'returns_policy',
      patterns: [
        /\b(return|refund|cancel|exchange)\b/i,
        /\breturn policy\b/i,
      ],
      confidence: 0.9,
    },
  ];

  for (const { intent, patterns, confidence } of intentPatterns) {
    for (const pattern of patterns) {
      if (pattern.test(lowerMessage)) {
        return { intent, confidence, entities };
      }
    }
  }

  // Default to part_lookup if entities found, otherwise out_of_scope
  if (partNumber || modelNumber) {
    return { intent: 'part_lookup', confidence: 0.7, entities };
  }

  return { intent: 'out_of_scope', confidence: 0.6, entities };
}
