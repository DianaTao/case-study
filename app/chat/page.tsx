'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore } from '@/lib/store';
import { apiClient } from '@/lib/api';
import { ChatHeader } from '@/components/ChatHeader';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatComposer } from '@/components/ChatComposer';
import { CartDrawer } from '@/components/CartDrawer';
import { QuickActions } from '@/components/QuickActions';
import type {
  ChatMessage as ChatMessageType,
  TroubleshootStepCard,
  Part,
  Card,
} from '@/lib/types';

const TROUBLESHOOT_FLOWS: Record<string, TroubleshootStepCard['data'][]> = {
  generic_flow: [
    {
      stepNumber: 1,
      totalSteps: 3,
      question: 'Is the appliance receiving power?',
      options: [
        { label: 'Yes', value: 'yes' },
        { label: 'No', value: 'no' },
      ],
      flowId: 'generic_flow',
    },
    {
      stepNumber: 2,
      totalSteps: 3,
      question: 'Is the water line connected and the shutoff valve open?',
      options: [
        { label: 'Yes', value: 'yes' },
        { label: 'No', value: 'no' },
      ],
      flowId: 'generic_flow',
    },
    {
      stepNumber: 3,
      totalSteps: 3,
      question: 'Has the water filter been replaced within the last 6 months?',
      options: [
        { label: 'Yes', value: 'yes' },
        { label: 'No', value: 'no' },
      ],
      flowId: 'generic_flow',
    },
  ],
};

export default function ChatPage() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const hasGreetedRef = useRef(false);

  const {
    sessionId,
    messages,
    applianceType,
    modelNumber,
    cartId,
    cart,
    isLoading,
    addMessage,
    setMessages,
    setCart,
    setLoading,
    resetSession,
  } = useChatStore();

  // No longer need to redirect - appliance type is parsed from natural language

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial greeting
  useEffect(() => {
    if (hasGreetedRef.current) return;
    const hasGreeting = messages.some(
      (message) =>
        message.role === 'assistant' &&
        (message.id === 'greeting' || message.id.startsWith('greeting_'))
    );
    if (messages.length === 0 && !hasGreeting) {
      hasGreetedRef.current = true;
      const greeting: ChatMessageType = {
        id: `greeting_${sessionId || Date.now()}_${Date.now()}`,
        role: 'assistant',
        content: `Hi! I'm here to help you with refrigerator and dishwasher parts. I can help you find parts, check compatibility, troubleshoot issues, and more. What do you need help with today?`,
        createdAt: new Date(),
      };
      addMessage(greeting);
    }
  }, [messages.length, addMessage, sessionId]);

  const uniqueMessages = useMemo(() => {
    const seen = new Set<string>();
    return messages.filter((message) => {
      if (seen.has(message.id)) return false;
      seen.add(message.id);
      return true;
    });
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: ChatMessageType = {
      id: `user_${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date(),
    };
    addMessage(userMessage);

    // Set loading
    setLoading(true);

    try {
      // Call API
      const response = await apiClient.sendMessage({
        sessionId,
        message: content,
        context: {
          appliance: applianceType,
          modelNumber,
        },
      });

      // Add assistant response
      const assistantMessage: ChatMessageType = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.assistantText,
        cards: response.cards,
        quickReplies: response.quickReplies,
        intent: response.intent,
        createdAt: new Date(),
      };
      addMessage(assistantMessage);
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Add error message
      const errorMessage: ChatMessageType = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        createdAt: new Date(),
      };
      addMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (partselectNumber: string) => {
    try {
      const updatedCart = await apiClient.addToCart(cartId, partselectNumber);
      setCart(updatedCart);
      
      // Show success message
      const successMessage: ChatMessageType = {
        id: `cart_${Date.now()}`,
        role: 'assistant',
        content: `Added ${partselectNumber} to your cart!`,
        createdAt: new Date(),
      };
      addMessage(successMessage);
    } catch (error) {
      console.error('Failed to add to cart:', error);
    }
  };

  const buildProductCard = (part: Part): Card => ({
    type: 'product',
    id: `product_${part.partselectNumber}_${Date.now()}`,
    data: {
      title: part.name,
      price: part.priceCents !== null && part.priceCents !== undefined ? part.priceCents / 100 : null,
      currency: 'USD',
      inStock:
        part.stockStatus === 'in_stock' ? true :
        part.stockStatus === 'out_of_stock' ? false :
        null,
      partselectNumber: part.partselectNumber,
      manufacturerPartNumber: part.manufacturerNumber,
      rating: part.rating,
      reviewCount: part.reviewCount ?? 0,
      imageUrl: part.imageUrl,
      productUrl: part.productUrl,
      install: {
        hasInstructions: part.hasInstallInstructions,
        hasVideos: part.hasVideos,
        links: part.installLinks,
      },
      cta: {
        action: 'add_to_cart',
        payload: { partselectNumber: part.partselectNumber },
      },
    },
  });

  const handleRefreshPrice = async (partselectNumber: string) => {
    try {
      const updated = await apiClient.refreshPrice(partselectNumber);
      addMessage({
        id: `price_refresh_${Date.now()}`,
        role: 'assistant',
        content: `Here is the latest price and availability for ${partselectNumber}:`,
        cards: [buildProductCard(updated)],
        createdAt: new Date(),
      });
    } catch (error) {
      console.error('Failed to refresh price:', error);
      addMessage({
        id: `price_refresh_error_${Date.now()}`,
        role: 'assistant',
        content: "I couldn't refresh that price right now. Please try again later.",
        createdAt: new Date(),
      });
    }
  };

  const handleTroubleshootAnswer = async (flowId: string, answer: string) => {
    // Find the current step from the last troubleshoot card
    const lastStepCard = [...messages]
      .reverse()
      .find((message) =>
        message.cards?.some(
          (card) => card.type === 'troubleshoot_step' && card.data.flowId === flowId
        )
      );

    const currentStepNumber =
      lastStepCard?.cards?.find((card) => card.type === 'troubleshoot_step')?.data.stepNumber ?? 1;

    // Add user answer
    addMessage({
      id: `trouble_answer_${Date.now()}`,
      role: 'user',
      content: `Answer: ${answer}`,
      createdAt: new Date(),
    });

    // Set loading
    setLoading(true);

    try {
      // Call backend with branching logic
      const response = await apiClient.sendTroubleshootAnswer(
        sessionId,
        flowId,
        currentStepNumber,
        answer,
        {
          appliance: applianceType,
          modelNumber,
        }
      );

      // Add assistant response
      const assistantMessage: ChatMessageType = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.assistantText,
        cards: response.cards,
        quickReplies: response.quickReplies,
        intent: response.intent,
        createdAt: new Date(),
      };
      addMessage(assistantMessage);
    } catch (error) {
      console.error('Failed to send troubleshoot answer:', error);
      addMessage({
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        createdAt: new Date(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    if (confirm('Are you sure you want to reset the conversation?')) {
      resetSession();
      router.push('/');
    }
  };

  return (
    <div className="flex flex-col h-screen bg-partselect-background">
      {/* Header */}
      <ChatHeader
        onReset={handleReset}
        onCartClick={() => setIsCartOpen(true)}
      />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-4 space-y-6">
          {uniqueMessages.length === 1 && <QuickActions onActionClick={handleSendMessage} />}
          
          {uniqueMessages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onAddToCart={handleAddToCart}
              onTroubleshootAnswer={handleTroubleshootAnswer}
              onTroubleshootExit={(flowId) => {
                handleSendMessage(`__EXIT_FLOW_${flowId}__`);
              }}
              onQuickReply={handleSendMessage}
              onRefreshPrice={handleRefreshPrice}
              onModelSubmit={async (modelNumber) => {
                // Update context and resend with model number
                await handleSendMessage(`Model: ${modelNumber}`);
              }}
              onViewCart={() => setIsCartOpen(true)}
              onLoadMore={async () => {
                await handleSendMessage('__SHOW_MORE_PARTS__');
              }}
            />
          ))}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Composer */}
      <ChatComposer
        onSend={handleSendMessage}
        isLoading={isLoading}
        placeholder={`Ask about ${applianceType || 'appliance'} parts...`}
      />

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        cart={cart}
      />
    </div>
  );
}
