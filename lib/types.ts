// Core domain types

export type ApplianceType = 'refrigerator' | 'dishwasher';
export type CompatibilityConfidence = 'exact' | 'likely' | 'unknown';
export type DocType = 'install' | 'troubleshoot' | 'faq' | 'policy' | 'qna';
export type IntentType =
  | 'part_lookup'
  | 'compatibility_check'
  | 'install_help'
  | 'troubleshoot'
  | 'cart_action'
  | 'order_support'
  | 'returns_policy'
  | 'out_of_scope';

// Part types
export interface Part {
  id: string;
  applianceType: ApplianceType;
  partselectNumber: string;
  manufacturerNumber?: string;
  name: string;
  brand?: string;
  priceCents?: number | null;
  stockStatus?: string | null;
  imageUrl?: string;
  productUrl?: string;
  description?: string;
  rating?: number;
  reviewCount: number;
  hasInstallInstructions: boolean;
  hasVideos: boolean;
  installLinks?: string[];
  installSummary?: string;
  commonSymptoms?: string[];
  notes?: string;
}

// Model types
export interface Model {
  id: string;
  applianceType: ApplianceType;
  modelNumber: string;
  brand?: string;
  modelUrl?: string;
}

// Compatibility types
export interface CompatibilityCheck {
  status: 'fits' | 'no_fit' | 'need_info';
  confidence: CompatibilityConfidence;
  evidenceUrl?: string;
  evidenceSnippet?: string;
  reason?: string;
}

// Chat types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cards?: Card[];
  quickReplies?: string[];
  intent?: IntentType;
  createdAt: Date;
}

export interface ChatSession {
  id: string;
  applianceType?: ApplianceType;
  modelNumber?: string;
  cartId?: string;
  lastIntent?: IntentType;
  messages: ChatMessage[];
  createdAt: Date;
}

// Card types for structured UI rendering
export type CardType =
  | 'product'
  | 'compatibility'
  | 'troubleshoot_step'
  | 'install_steps'
  | 'ask_model_number'
  | 'model_capture'
  | 'out_of_scope'
  | 'order_support'
  | 'product_list'
  | 'cart_summary'
  | 'compare_parts'
  | 'show_more'
  | 'action_suggestion';

export interface BaseCard {
  type: CardType;
  id: string;
}

export interface ProductCard extends BaseCard {
  type: 'product';
  data: {
    title: string;
    price?: number | null;
    currency: string;
    inStock?: boolean | null;
    partselectNumber: string;
    manufacturerPartNumber?: string;
    rating?: number;
    reviewCount: number;
    imageUrl?: string;
    productUrl?: string;
    provenance?: string | null; // NEW: Shows data source/timestamp
    install?: {
      hasInstructions: boolean;
      hasVideos: boolean;
      links?: string[];
    };
    cta: {
      action: 'add_to_cart' | 'view_details' | 'check_fit';
      payload?: any;
    };
  };
}

export interface CompatibilityCard extends BaseCard {
  type: 'compatibility';
  data: {
    status: 'fits' | 'no_fit' | 'need_info';
    partselectNumber: string;
    modelNumber?: string;
    reason: string;
    confidence?: 'exact' | 'likely' | 'unknown';
    evidence?: {
      url?: string;
      snippet?: string;
    };
    modelPageUrl?: string; // Link to model's parts page
  };
}

export interface TroubleshootStepCard extends BaseCard {
  type: 'troubleshoot_step';
  data: {
    stepNumber: number;
    totalSteps: number;
    question: string;
    options: Array<{
      label: string;
      value: string;
    }>;
    flowId: string;
    flowName?: string; // e.g. "Ice maker troubleshooting"
    canExit?: boolean; // default true
  };
}

export interface InstallStepsCard extends BaseCard {
  type: 'install_steps';
  data: {
    partselectNumber: string;
    difficulty?: 'easy' | 'moderate' | 'hard';
    estimatedTimeMinutes?: number;
    tools?: string[];
    safetyNotes?: string[];
    summary?: string;
    steps: Array<{
      stepNumber: number;
      instruction: string;
      safetyNote?: string;
    }>;
    links?: Array<{
      type: 'video' | 'manual' | 'diagram';
      url: string;
      label: string;
    }>;
  };
}

export interface AskModelNumberCard extends BaseCard {
  type: 'ask_model_number';
  data: {
    reason: string;
    helpUrl?: string;
  };
}

export interface OutOfScopeCard extends BaseCard {
  type: 'out_of_scope';
  data: {
    message: string;
    exampleQueries?: string[];
    suggestedActions?: string[];
  };
}

export interface ModelCaptureCard extends BaseCard {
  type: 'model_capture';
  data: {
    title: string;
    body: string;
    canSkip: boolean;
    reason?: string;
  };
}

export interface CartSummaryCard extends BaseCard {
  type: 'cart_summary';
  data: {
    itemCount: number;
    subtotalCents: number;
    currency: string;
  };
}

export interface ComparePartsCard extends BaseCard {
  type: 'compare_parts';
  data: {
    parts: Array<{
      partselectNumber: string;
      name: string;
      likelihood?: 'high' | 'medium' | 'low';
      priceCents?: number;
      difficulty?: 'easy' | 'moderate' | 'hard';
    }>;
  };
}

export interface ShowMoreCard extends BaseCard {
  type: 'show_more';
  data: {
    totalAvailable: number;
    shown: number;
    action: string;
  };
}

export interface ActionSuggestionCard extends BaseCard {
  type: 'action_suggestion';
  data: {
    label: string;
    action: string;
  };
}

export interface ProductListCard extends BaseCard {
  type: 'product_list';
  data: {
    title: string;
    products: ProductCard['data'][];
  };
}

export type Card =
  | ProductCard
  | CompatibilityCard
  | TroubleshootStepCard
  | InstallStepsCard
  | AskModelNumberCard
  | ModelCaptureCard
  | OutOfScopeCard
  | ProductListCard
  | CartSummaryCard
  | ComparePartsCard
  | ShowMoreCard
  | ActionSuggestionCard;

// API request/response types
export interface ChatRequest {
  sessionId: string;
  message: string;
  context?: {
    appliance?: ApplianceType;
    modelNumber?: string;
    locale?: string;
  };
}

export interface ChatResponse {
  version?: string;
  intent?: IntentType;
  source?: 'db' | 'scraper+llm' | 'rules' | 'mixed';
  assistantText: string;
  cards?: Card[];
  quickReplies?: string[];
  events?: Array<{
    type: string;
    name: string;
    data?: any;
  }>;
}

// Cart types
export interface CartItem {
  partselectNumber: string;
  quantity: number;
  addedAt: Date;
  part?: Part;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalCents: number;
  createdAt: Date;
  updatedAt: Date;
}

// Troubleshooting types
export interface TroubleshootingFlow {
  id: string;
  applianceType: ApplianceType;
  symptomKey: string;
  currentStep: number;
  answers: Record<string, string>;
  recommendations?: Array<{
    cause: string;
    confidence: number;
    parts: string[]; // partselect numbers
  }>;
}

// Tool types (for agent orchestration)
export interface Tool {
  name: string;
  description: string;
  inputSchema: any;
  execute: (input: any) => Promise<any>;
}

export interface ToolCall {
  tool: string;
  input: any;
  output?: any;
  error?: string;
}
