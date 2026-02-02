'use client';

import { formatDate } from '@/lib/utils';
import { ProductCard } from './cards/ProductCard';
import { CompatibilityCard } from './cards/CompatibilityCard';
import { TroubleshootStepCard } from './cards/TroubleshootStepCard';
import { InstallStepsCard } from './cards/InstallStepsCard';
import { OutOfScopeCard } from './cards/OutOfScopeCard';
import { ModelCaptureCard } from './cards/ModelCaptureCard';
import { CartSummaryCard } from './cards/CartSummaryCard';
import { ComparePartsCard } from './cards/ComparePartsCard';
import { ShowMoreCard } from './cards/ShowMoreCard';
import { ActionSuggestionCard } from './cards/ActionSuggestionCard';
import type { ChatMessage as ChatMessageType, Card } from '@/lib/types';
import { User, Bot } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
  onAddToCart?: (partselectNumber: string) => void;
  onTroubleshootAnswer?: (flowId: string, answer: string) => void;
  onTroubleshootExit?: (flowId: string) => void;
  onQuickReply?: (reply: string) => void;
  onRefreshPrice?: (partselectNumber: string) => void;
  onModelSubmit?: (modelNumber: string) => void;
  onViewCart?: () => void;
  onLoadMore?: () => void;
}

export function ChatMessage({
  message,
  onAddToCart,
  onTroubleshootAnswer,
  onTroubleshootExit,
  onQuickReply,
  onRefreshPrice,
  onModelSubmit,
  onViewCart,
  onLoadMore,
}: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-gray-200' : 'bg-partselect-primary'
        }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-gray-600" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
        {/* Text */}
        <div
          className={`px-4 py-2 rounded-lg ${
            isUser
              ? 'bg-partselect-primary text-white'
              : 'bg-partselect-surface text-partselect-text-primary'
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Cards */}
        {message.cards && message.cards.length > 0 && (
          <div className="space-y-3 w-full">
            {message.cards.map((card) =>
              renderCard(
                card,
                onAddToCart,
                onTroubleshootAnswer,
                onTroubleshootExit,
                onQuickReply,
                onRefreshPrice,
                onModelSubmit,
                onViewCart,
                onLoadMore
              )
            )}
          </div>
        )}

        {/* Quick Replies */}
        {message.quickReplies && message.quickReplies.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.quickReplies.map((reply, index) => (
              <button
                key={index}
                onClick={() => onQuickReply?.(reply)}
                className="px-3 py-1 bg-white border border-partselect-border text-partselect-primary rounded-full text-sm hover:bg-partselect-surface transition-colors"
              >
                {reply}
              </button>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-xs text-partselect-text-secondary">
          {formatDate(message.createdAt)}
        </span>
      </div>
    </div>
  );
}

function renderCard(
  card: Card,
  onAddToCart?: (partselectNumber: string) => void,
  onTroubleshootAnswer?: (flowId: string, answer: string) => void,
  onTroubleshootExit?: (flowId: string) => void,
  onQuickReply?: (reply: string) => void,
  onRefreshPrice?: (partselectNumber: string) => void,
  onModelSubmit?: (modelNumber: string) => void,
  onViewCart?: () => void,
  onLoadMore?: () => void
) {
  switch (card.type) {
    case 'product':
      return (
        <ProductCard
          key={card.id}
          card={card}
          onAddToCart={onAddToCart}
          onRefreshPrice={onRefreshPrice}
        />
      );
    case 'compatibility':
      return <CompatibilityCard key={card.id} card={card} />;
    case 'troubleshoot_step':
      return (
        <TroubleshootStepCard
          key={card.id}
          card={card}
          onAnswer={onTroubleshootAnswer}
          onExitFlow={onTroubleshootExit}
        />
      );
    case 'install_steps':
      return <InstallStepsCard key={card.id} card={card} />;
    case 'model_capture':
      return (
        <ModelCaptureCard
          key={card.id}
          card={card}
          onModelSubmit={onModelSubmit}
        />
      );
    case 'cart_summary':
      return (
        <CartSummaryCard
          key={card.id}
          card={card}
          onViewCart={onViewCart}
        />
      );
    case 'compare_parts':
      return (
        <ComparePartsCard
          key={card.id}
          card={card}
          onPartClick={(ps) => onQuickReply?.(`Show me part ${ps}`)}
        />
      );
    case 'show_more':
      return (
        <ShowMoreCard
          key={card.id}
          card={card}
          onLoadMore={onLoadMore}
        />
      );
    case 'action_suggestion':
      return (
        <ActionSuggestionCard
          key={card.id}
          card={card}
          onAction={(action) => onQuickReply?.(action)}
        />
      );
    case 'out_of_scope':
      return <OutOfScopeCard key={card.id} card={card} onActionClick={onQuickReply} />;
    default:
      // Unknown card fallback
      return (
        <div
          key={card.id}
          className="rounded-lg border bg-muted p-4 text-sm text-muted-foreground"
        >
          New assistant content is available but your client version can't render this card type yet.
        </div>
      );
  }
}
