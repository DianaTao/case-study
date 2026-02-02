import type { ChatRequest, ChatResponse, Part, Cart } from './types';

// Python backend URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const normalizedBase = this.baseUrl.replace(/\/$/, '');
    const attemptFetch = async (baseUrl: string): Promise<Response> => {
      const url = `${baseUrl}${endpoint}`;
      return fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
    };

    let response: Response;
    try {
      response = await attemptFetch(normalizedBase);
    } catch (error) {
      const fallbackBase = 'http://127.0.0.1:8000';
      if (normalizedBase !== fallbackBase) {
        response = await attemptFetch(fallbackBase);
      } else {
        throw new Error('API is unreachable. Is the backend running on port 8000?');
      }
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        console.error('Failed to parse error response:', e);
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Chat
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const payload = {
      session_id: request.sessionId,
      message: request.message,
      context: request.context,
    };
    const raw = await this.request<{
      version?: string;
      intent?: string;
      source?: string;
      assistant_text: string;
      cards?: any[];
      quick_replies?: string[];
      events?: any[];
    }>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return {
      version: raw.version,
      intent: raw.intent as any,
      source: raw.source as any,
      assistantText: raw.assistant_text,
      cards: raw.cards,
      quickReplies: raw.quick_replies,
      events: raw.events,
    };
  }

  async sendTroubleshootAnswer(
    sessionId: string,
    flowId: string,
    step: number,
    answer: string,
    context: Record<string, any>
  ): Promise<ChatResponse> {
    const payload = {
      session_id: sessionId,
      flow_id: flowId,
      step,
      answer,
      context: context || {},
    };
    const raw = await this.request<{
      version?: string;
      intent?: string;
      source?: string;
      assistant_text: string;
      cards?: any[];
      quick_replies?: string[];
      events?: any[];
    }>('/api/chat/troubleshoot-answer', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return {
      version: raw.version,
      intent: raw.intent as any,
      source: raw.source as any,
      assistantText: raw.assistant_text,
      cards: raw.cards,
      quickReplies: raw.quick_replies,
      events: raw.events,
    };
  }

  // Parts
  async searchParts(query: string, applianceType?: string): Promise<Part[]> {
    const params = new URLSearchParams({ q: query });
    if (applianceType) params.append('appliance_type', applianceType);
    
    return this.request<Part[]>(`/api/parts/search?${params}`);
  }

  async getPart(partselectNumber: string): Promise<Part> {
    return this.request<Part>(`/api/parts/${partselectNumber}`);
  }

  async refreshPrice(partselectNumber: string): Promise<Part> {
    return this.request<Part>('/api/parts/refresh-price', {
      method: 'POST',
      body: JSON.stringify({ partselect_number: partselectNumber }),
    });
  }

  // Compatibility
  async checkCompatibility(partselectNumber: string, modelNumber: string): Promise<{
    status: 'fits' | 'no_fit' | 'need_info';
    confidence: 'exact' | 'likely' | 'unknown';
    message: string;
    evidence_url?: string;
    evidence_snippet?: string;
  }> {
    return this.request('/api/compatibility', {
      method: 'POST',
      body: JSON.stringify({
        partselect_number: partselectNumber,
        model_number: modelNumber,
      }),
    });
  }

  // Troubleshooting
  async startTroubleshooting(applianceType: string, symptomText: string): Promise<any> {
    return this.request('/api/troubleshoot/start', {
      method: 'POST',
      body: JSON.stringify({ applianceType, symptomText }),
    });
  }

  async answerTroubleshooting(flowId: string, answer: string): Promise<any> {
    return this.request('/api/troubleshoot/answer', {
      method: 'POST',
      body: JSON.stringify({ flowId, answer }),
    });
  }

  // Cart
  async getCart(cartId: string): Promise<Cart> {
    return this.request<Cart>(`/api/cart/${cartId}`);
  }

  async addToCart(cartId: string, partselectNumber: string, quantity: number = 1): Promise<Cart> {
    return this.request<Cart>('/api/cart/add', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId,
        partselect_number: partselectNumber,
        quantity,
      }),
    });
  }

  async updateCartItem(cartId: string, partselectNumber: string, quantity: number): Promise<Cart> {
    return this.request<Cart>('/api/cart/update', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId,
        partselect_number: partselectNumber,
        quantity,
      }),
    });
  }

  // Policy
  async getReturnsPolicy(): Promise<string> {
    return this.request<string>('/api/policy/returns');
  }

  async getOrderHelp(query: string): Promise<any> {
    return this.request('/api/order/help', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }
}

export const apiClient = new ApiClient();
