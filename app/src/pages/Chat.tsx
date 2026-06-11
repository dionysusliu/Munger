import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Send, ThumbsUp, ThumbsDown, MessageSquare, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  chatSend,
  chatMessages,
  feedbackRate,
  type ChatCitation,
} from '@/lib/api';

const STORAGE_KEY = 'munger_chat_session_id';

interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  citations?: ChatCitation[];
  bridge?: number[];
  rating?: 1 | -1;
}

export default function Chat() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load history once on mount if a session was stored
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return;
    const sid = Number(stored);
    setSessionId(sid);

    let cancelled = false;

    async function loadHistory() {
      try {
        const data = await chatMessages(sid);
        if (cancelled) return;
        const mapped: ChatMessage[] = data.messages.map((m) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          citations: m.meta?.citations,
          bridge: m.meta?.bridge,
        }));
        setMessages(mapped);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load history');
        }
      }
    }

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, []); // intentionally run once on mount

  // Auto-scroll to bottom on new messages or while sending
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  function handleNewSession() {
    localStorage.removeItem(STORAGE_KEY);
    setSessionId(null);
    setMessages([]);
    setError(null);
    setInput('');
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);
    setError(null);

    try {
      const res = await chatSend(text, sessionId ?? undefined);
      const newSid = res.session_id;
      setSessionId(newSid);
      localStorage.setItem(STORAGE_KEY, String(newSid));

      const assistantMsg: ChatMessage = {
        id: res.assistant_message_id,
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        bridge: res.bridge,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the optimistic user message
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  async function handleRate(msg: ChatMessage, rating: 1 | -1) {
    if (!msg.id) return;
    try {
      await feedbackRate(msg.id, rating);
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, rating } : m))
      );
    } catch {
      // Silently ignore feedback errors
    }
  }

  function resolveBridgeName(id: number, citations: ChatCitation[] | undefined): string {
    const match = citations?.find((c) => c.entity_id === id);
    return match ? match.name : `#${id}`;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 md:px-8 py-4 border-b border-amber-800/20 flex-shrink-0">
        <motion.h1
          className="font-display text-display-lg text-text-primary"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Chat
        </motion.h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleNewSession}
          className="text-text-secondary hover:text-text-primary gap-1.5"
        >
          <Plus className="w-4 h-4" />
          New session
        </Button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 md:px-8 py-6">
        {messages.length === 0 && !sending ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 text-text-muted opacity-40" />
              <p className="text-text-muted text-body-md">Ask your knowledge base…</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-amber-900/30 border border-amber-800/20 text-text-primary'
                      : 'bg-bg-surface border border-amber-800/10 text-text-secondary'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <>
                      <article
                        className={[
                          'prose prose-invert prose-sm max-w-none',
                          'prose-p:text-text-secondary prose-headings:text-text-primary',
                          'prose-a:text-amber-400 prose-strong:text-text-primary',
                          'prose-code:text-amber-300 prose-li:text-text-secondary',
                        ].join(' ')}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </article>

                      {/* Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {msg.citations.map((c) =>
                            c.wiki ? (
                              <Link
                                key={c.entity_id}
                                to={`/wiki/${c.wiki.slug}`}
                                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-amber-900/20 border border-amber-800/20 text-amber-400 hover:bg-amber-900/40 transition-colors"
                              >
                                {c.name}
                              </Link>
                            ) : (
                              <span
                                key={c.entity_id}
                                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-bg-elevated border border-amber-800/10 text-text-muted"
                              >
                                {c.name}
                              </span>
                            )
                          )}
                        </div>
                      )}

                      {/* Bridge path */}
                      {msg.bridge && msg.bridge.length >= 2 && (
                        <p className="mt-1.5 text-xs text-text-muted">
                          Bridge:{' '}
                          {msg.bridge
                            .map((id) => resolveBridgeName(id, msg.citations))
                            .join(' → ')}
                        </p>
                      )}

                      {/* Rating */}
                      <div className="mt-2 flex items-center gap-1">
                        <button
                          onClick={() => void handleRate(msg, 1)}
                          disabled={!msg.id}
                          className={`p-1 rounded transition-colors disabled:opacity-30 ${
                            msg.rating === 1
                              ? 'text-amber-400'
                              : 'text-text-muted hover:text-text-secondary'
                          }`}
                          aria-label="Helpful"
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => void handleRate(msg, -1)}
                          disabled={!msg.id}
                          className={`p-1 rounded transition-colors disabled:opacity-30 ${
                            msg.rating === -1
                              ? 'text-amber-400'
                              : 'text-text-muted hover:text-text-secondary'
                          }`}
                          aria-label="Not helpful"
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  )}
                </div>
              </motion.div>
            ))}

            {/* Sending indicator */}
            {sending && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="bg-bg-surface border border-amber-800/10 rounded-2xl px-4 py-3">
                  <div className="flex gap-1 items-center h-4">
                    <span className="w-1.5 h-1.5 bg-amber-400/60 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-amber-400/60 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-amber-400/60 rounded-full animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 md:px-8 py-2 flex-shrink-0">
          <p className="text-body-sm text-red-400 bg-red-900/10 border border-red-800/20 rounded-md px-3 py-2">
            {error}
          </p>
        </div>
      )}

      {/* Input */}
      <div className="px-6 md:px-8 py-4 border-t border-amber-800/20 flex-shrink-0">
        <div className="flex items-end gap-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            disabled={sending}
            rows={1}
            className="flex-1 resize-none bg-bg-surface border-amber-800/20 text-text-primary placeholder:text-text-muted focus-visible:border-amber-700/50 min-h-[44px] max-h-[200px]"
          />
          <Button
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
            size="icon"
            className="bg-amber-600 hover:bg-amber-500 text-white flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
