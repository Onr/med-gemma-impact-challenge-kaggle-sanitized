import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, MessageImage, Phase, ModelKey } from '../types';
import { PHASE_COLORS } from '../constants';
import ImageUpload, { ImageData } from './ImageUpload';
import ModelSelector, { modelSupportsImages } from './ModelSelector';

interface ChatPanelProps {
  messages: Message[];
  currentPhase: Phase;
  onSendMessage: (text: string, images?: MessageImage[]) => void;
  isLoading: boolean;
  draftInput: string;
  onDraftInputConsumed: () => void;
  selectedModel: ModelKey;
  onModelChange: (model: ModelKey) => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  currentPhase,
  onSendMessage,
  isLoading,
  draftInput,
  onDraftInputConsumed,
  selectedModel,
  onModelChange
}) => {
  const [inputText, setInputText] = useState('');
  const [pendingImages, setPendingImages] = useState<ImageData[]>([]);
  const [showImageUpload, setShowImageUpload] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isListening, setIsListening] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('medgemma-tts-enabled') === 'true';
  });
  const [isSpeaking, setIsSpeaking] = useState(false);
  const spokenMessageIdsRef = useRef<Set<string>>(new Set());

  const supportsImages = modelSupportsImages(selectedModel);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (draftInput) {
      setInputText(prev => prev ? `${prev} ${draftInput}` : draftInput);
      onDraftInputConsumed();
    }
  }, [draftInput, onDraftInputConsumed]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem('medgemma-tts-enabled', String(ttsEnabled));
  }, [ttsEnabled]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    const onSpeechStart = () => setIsSpeaking(true);
    const onSpeechEnd = () => setIsSpeaking(false);
    window.speechSynthesis.addEventListener('start', onSpeechStart);
    window.speechSynthesis.addEventListener('end', onSpeechEnd);
    window.speechSynthesis.addEventListener('error', onSpeechEnd);

    return () => {
      window.speechSynthesis.removeEventListener('start', onSpeechStart);
      window.speechSynthesis.removeEventListener('end', onSpeechEnd);
      window.speechSynthesis.removeEventListener('error', onSpeechEnd);
    };
  }, []);

  const stripForSpeech = useCallback((text: string) => {
    return text
      .replace(/```[\s\S]*?```/g, ' ')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[>#*_~|-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }, []);

  const speakText = useCallback((text: string, role: 'user' | 'model') => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported in this browser.');
      return;
    }
    const cleaned = stripForSpeech(text);
    if (!cleaned) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(cleaned);
    utterance.rate = role === 'model' ? 1.0 : 1.04;
    utterance.pitch = role === 'model' ? 1.0 : 1.08;
    utterance.lang = 'en-US';
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, [stripForSpeech]);

  const stopSpeech = useCallback(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  useEffect(() => {
    if (!ttsEnabled || messages.length === 0) return;
    const latest = messages[messages.length - 1];
    if (spokenMessageIdsRef.current.has(latest.id)) return;
    spokenMessageIdsRef.current.add(latest.id);
    speakText(latest.content, latest.role);
  }, [messages, speakText, ttsEnabled]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if ((inputText.trim() || pendingImages.length > 0) && !isLoading) {
      // Convert pending images to MessageImage format
      const messageImages: MessageImage[] | undefined = pendingImages.length > 0
        ? pendingImages.map(img => ({
          mimeType: img.mimeType,
          data: img.base64 || '',
          preview: img.preview
        }))
        : undefined;

      onSendMessage(inputText || 'Analyze this image', messageImages);
      setInputText('');
      setPendingImages([]);
      setShowImageUpload(false);
    }
  };

  const handleImagesChange = useCallback((images: ImageData[]) => {
    setPendingImages(images);
  }, []);

  // Basic Speech Recognition (Chrome/Edge only)
  const toggleVoice = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInputText(prev => prev ? `${prev} ${transcript}` : transcript);
      };

      recognition.start();
    } else {
      alert("Speech recognition not supported in this browser.");
    }
  };

  // Helper to render phase divider
  const renderPhaseDivider = (phase: Phase) => (
    <div className="flex items-center gap-4 py-4 opacity-70">
      <div className="h-[1px] flex-1" style={{ backgroundColor: 'var(--color-border)' }}></div>
      <div className="text-[10px] font-bold uppercase tracking-widest rounded-full px-3 py-1" style={{ color: 'var(--color-text-muted)', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
        Entering {phase}
      </div>
      <div className="h-[1px] flex-1" style={{ backgroundColor: 'var(--color-border)' }}></div>
    </div>
  );

  // Helper to render extracted data visualizations inline
  const renderExtractedData = (data: any) => {
    if (!data) return null;

    const cardClass = "mt-3 rounded-lg p-3 text-xs border backdrop-blur-sm";
    const titleClass = "font-bold uppercase tracking-wider opacity-70 mb-2 border-b pb-1";

    switch (data.type) {
      case 'PICO_UPDATE':
        return (
          <div className={cardClass} style={{ backgroundColor: "var(--color-bg-tertiary)", borderColor: "var(--color-border)" }}>
            <div className={titleClass} style={{ borderColor: "var(--color-border)", color: "var(--color-text-secondary)" }}>Updated PICO Context</div>
            <div className="grid grid-cols-2 gap-2">
              <div><span className="text-sky-400 font-bold">P:</span> {data.data.patient || '-'}</div>
              <div><span className="text-emerald-400 font-bold">I:</span> {data.data.intervention || '-'}</div>
              <div><span className="text-amber-400 font-bold">C:</span> {data.data.comparison || '-'}</div>
              <div><span className="text-rose-400 font-bold">O:</span> {data.data.outcome || '-'}</div>
            </div>
          </div>
        );
      case 'REFERENCE_UPDATE':
        return (
          <div className={cardClass} style={{ backgroundColor: "var(--color-bg-tertiary)", borderColor: "var(--color-border)" }}>
            <div className={titleClass} style={{ borderColor: "var(--color-border)", color: "var(--color-text-secondary)" }}>Added References ({data.data.length})</div>
            <ul className="space-y-2">
              {data.data.map((ref: any, i: number) => (
                <li key={i} className="flex gap-2">
                  <span className="bg-emerald-500/20 text-emerald-500 px-1 rounded h-fit">{ref.type}</span>
                  <div>
                    {ref.url ? (
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-sky-500 hover:text-sky-400 hover:underline transition-colors inline-flex items-center gap-1"
                      >
                        {ref.title}
                        <span className="material-symbols-outlined text-xs">open_in_new</span>
                      </a>
                    ) : (
                      <div className="font-semibold">{ref.title}</div>
                    )}
                    <div className="opacity-60">{ref.source} ({ref.year})</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        );
      case 'APPRAISAL_UPDATE':
        return (
          <div className={cardClass} style={{ backgroundColor: "var(--color-bg-tertiary)", borderColor: "var(--color-border)" }}>
            <div className={titleClass} style={{ borderColor: "var(--color-border)", color: "var(--color-text-secondary)" }}>Critical Appraisal ({data.data.length})</div>
            <ul className="space-y-2">
              {data.data.map((item: any, i: number) => {
                const verdictColor = item.verdict === 'Positive' ? 'text-emerald-500' : item.verdict === 'Negative' ? 'text-rose-500' : 'text-amber-500';
                const verdictBg = item.verdict === 'Positive' ? 'bg-emerald-500/20' : item.verdict === 'Negative' ? 'bg-rose-500/20' : 'bg-amber-500/20';
                return (
                  <li key={i} className="flex gap-2">
                    <span className={`${verdictBg} ${verdictColor} px-2 py-0.5 rounded text-[10px] font-bold uppercase h-fit`}>{item.verdict}</span>
                    <div>
                      <div className="font-semibold">{item.title}</div>
                      <div className="opacity-60 text-xs mt-0.5">{item.description}</div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      case 'APPLY_UPDATE':
        return (
          <div className={cardClass} style={{ backgroundColor: "var(--color-bg-tertiary)", borderColor: "var(--color-border)" }}>
            <div className={titleClass} style={{ borderColor: "var(--color-border)", color: "var(--color-text-secondary)" }}>Clinical Actions ({data.data.length})</div>
            <ul className="list-disc pl-4 space-y-1">
              {data.data.map((item: any, i: number) => (
                <li key={i}>
                  <span className="font-medium text-purple-400">{item.action}</span>
                </li>
              ))}
            </ul>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full w-full relative z-20 theme-transition bg-transparent">
      {/* Header */}
      <div className="p-4 flex justify-between items-center backdrop-blur-md" style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
        <h2 className="text-lg font-bold flex items-center gap-2 tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
          <span className="material-symbols-outlined text-sky-500">medical_services</span>
          MedGemma
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setTtsEnabled(prev => !prev)}
            className={`text-xs font-medium px-2 py-1 rounded transition-colors ${ttsEnabled ? 'bg-emerald-500/20 text-emerald-400' : ''}`}
            style={ttsEnabled ? {} : { color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}
            title="Auto-read new user and assistant messages"
          >
            TTS {ttsEnabled ? 'On' : 'Off'}
          </button>
          {isSpeaking && (
            <button
              type="button"
              onClick={stopSpeech}
              className="text-xs font-medium px-2 py-1 rounded bg-rose-500/20 text-rose-400"
              title="Stop speaking"
            >
              Stop
            </button>
          )}
          {/* Model Selector (Compact) */}
          <ModelSelector
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            compact={true}
          />
          <div className="text-xs font-medium px-2 py-1 rounded" style={{ color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
            {currentPhase} Phase
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-hide bg-transparent">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3 opacity-60" style={{ color: 'var(--color-text-muted)' }}>
            <div className="p-4 rounded-full" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
              <span className="material-symbols-outlined text-4xl">chat_bubble_outline</span>
            </div>
            <p className="text-sm font-medium">Start by describing your clinical case.</p>
          </div>
        )}

        {messages.map((msg, index) => {
          // Check previous message phase to determine divider
          const prevPhase = index > 0 ? messages[index - 1].phase : null;
          // Divider shows if current message starts a NEW phase compared to previous
          const showDivider = index > 0 && msg.phase && prevPhase && msg.phase !== prevPhase;
          const msgPhase = msg.phase || Phase.ASK;

          return (
            <React.Fragment key={msg.id}>
              {showDivider && renderPhaseDivider(msgPhase)}
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-3`}>
                <div
                  className={`max-w-[90%] rounded-2xl p-3.5 text-sm leading-relaxed shadow-sm ${msg.role === 'user'
                    ? 'bg-sky-600 text-white rounded-br-none'
                    : 'rounded-bl-none liquid-surface'
                    }`}
                  style={msg.role === 'model' ? {
                    borderLeft: `3px solid ${PHASE_COLORS[msgPhase]}`,
                    backgroundColor: 'var(--color-bg-secondary)',
                    color: 'var(--color-text-primary)',
                    border: '1px solid var(--color-border)'
                  } : {}}
                >
                  {msg.role === 'user' ? (
                    <div>
                      {/* Display attached images */}
                      {msg.images && msg.images.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                          {msg.images.map((img, idx) => (
                            <div key={idx} className="relative w-24 h-24 rounded-lg overflow-hidden border border-sky-400/30">
                              <img
                                src={img.preview || `data:${img.mimeType};base64,${img.data}`}
                                alt={`Attached image ${idx + 1}`}
                                className="w-full h-full object-cover"
                              />
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  ) : (
                    <div>
                      <ReactMarkdown
                        components={{
                          p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                          ul: ({ node, ...props }) => <ul className="list-disc ml-4 mb-2 space-y-1" {...props} />,
                          ol: ({ node, ...props }) => <ol className="list-decimal ml-4 mb-2 space-y-1" {...props} />,
                          li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                          strong: ({ node, ...props }) => <strong className="font-semibold text-sky-500" {...props} />,
                          a: ({ node, ...props }) => <a className="text-sky-500 hover:underline" target="_blank" {...props} />,
                          h1: ({ node, ...props }) => <h1 className="text-lg font-bold mb-2" {...props} />,
                          h2: ({ node, ...props }) => <h2 className="text-base font-bold mb-2 mt-3" {...props} />,
                          h3: ({ node, ...props }) => <h3 className="text-sm font-bold mb-1 mt-2" {...props} />,
                          blockquote: ({ node, ...props }) => <blockquote className="border-l-2 border-slate-400 pl-3 italic text-slate-500 my-2" {...props} />,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                      {/* Inline Extracted Data Visualization */}
                      {msg.role === 'model' && msg.extractedData && renderExtractedData(msg.extractedData)}
                    </div>
                  )}
                  <div className={`mt-2 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <button
                      type="button"
                      onClick={() => speakText(msg.content, msg.role)}
                      className={`text-[11px] px-2 py-1 rounded inline-flex items-center gap-1 ${msg.role === 'user' ? 'bg-white/20 hover:bg-white/30 text-white' : 'hover:opacity-80'}`}
                      style={msg.role === 'user' ? {} : { color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}
                      title="Read this message aloud"
                    >
                      <span className="material-symbols-outlined text-sm">volume_up</span>
                      Speak
                    </button>
                  </div>
                </div>
              </div>
            </React.Fragment>
          );
        })}
        {isLoading && (
          <div className="thinking-indicator" aria-live="polite">
            <div className="thinking-shimmer" />
            <span className="thinking-label">MedGemma is thinking</span>
            <span className="thinking-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 space-y-2 flex-shrink-0 backdrop-blur-md" style={{ backgroundColor: 'var(--color-bg-secondary)', borderTop: '1px solid var(--color-border)' }}>
        {/* Image Upload Area */}
        {supportsImages && showImageUpload && (
          <ImageUpload
            onImagesChange={handleImagesChange}
            maxImages={4}
            disabled={isLoading}
          />
        )}

        {/* Pending images preview (compact) */}
        {pendingImages.length > 0 && !showImageUpload && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="material-symbols-outlined text-sm text-emerald-400">image</span>
            <span>{pendingImages.length} image(s) attached</span>
            <button
              onClick={() => setShowImageUpload(true)}
              className="text-sky-400 hover:underline"
            >
              Edit
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-end gap-2 relative">
          {/* Image upload toggle button */}
          {supportsImages && (
            <button
              type="button"
              onClick={() => setShowImageUpload(!showImageUpload)}
              className={`p-3 rounded-xl transition-all flex-shrink-0 ${showImageUpload || pendingImages.length > 0
                ? 'bg-sky-600 text-white'
                : 'hover:opacity-80'
                }`}
              style={showImageUpload || pendingImages.length > 0 ? {} : { backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-muted)', border: '1px solid var(--color-border)' }}
              title="Add medical image"
            >
              <span className="material-symbols-outlined text-xl">add_photo_alternate</span>
            </button>
          )}

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={pendingImages.length > 0
              ? 'Describe what to analyze in the image...'
              : `Ask about ${currentPhase.toLowerCase()}...`
            }
            className="w-full rounded-xl py-3.5 pl-4 pr-12 resize-none focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-[52px] max-h-[120px] scrollbar-hide text-sm transition-all"
            style={{ backgroundColor: 'var(--color-bg-input)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }}
            rows={1}
          />
          <button
            type="button"
            onClick={toggleVoice}
            className={`absolute right-14 bottom-3 p-1.5 rounded-full transition-colors ${isListening ? 'bg-red-500/20 text-red-500 animate-pulse' : 'hover:opacity-80'
              }`}
            style={isListening ? {} : { color: 'var(--color-text-muted)' }}
            title="Voice Input"
          >
            <span className="material-symbols-outlined text-lg">mic</span>
          </button>

          <button
            type="submit"
            disabled={(!inputText.trim() && pendingImages.length === 0) || isLoading}
            className="p-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-xl transition-all shadow-lg shadow-sky-900/20 flex-shrink-0"
          >
            <span className="material-symbols-outlined text-xl">send</span>
          </button>
        </form>

        {/* Image support hint */}
        {!supportsImages && (
          <p className="text-[10px] text-center" style={{ color: 'var(--color-text-muted)' }}>
            Switch to a multimodal model (MedGemma 4B/27B MM) to enable image analysis
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatPanel;
