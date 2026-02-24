import React from 'react';
import { ModelKey } from '../types';

interface ModelOption {
  id: ModelKey;
  name: string;
  supportsImages: boolean;
  description: string;
  icon: string;
}

const MODELS: ModelOption[] = [
  {
    id: 'medgemma-4b-it',
    name: 'MedGemma 4B',
    supportsImages: true,
    description: 'Local GPU • Fast multimodal',
    icon: 'speed'
  },
  {
    id: 'medgemma-27b-text',
    name: 'MedGemma 27B',
    supportsImages: false,
    description: 'Cloud API • Advanced reasoning',
    icon: 'psychology'
  },
  {
    id: 'medgemma-27b-mm',
    name: 'MedGemma 27B MM',
    supportsImages: true,
    description: 'Cloud API • Advanced multimodal',
    icon: 'auto_awesome'
  },
  {
    id: 'gemini-flash',
    name: 'Gemini Flash',
    supportsImages: true,
    description: 'Cloud API • General fallback',
    icon: 'bolt'
  }
];

interface ModelSelectorProps {
  selectedModel: ModelKey;
  onModelChange: (model: ModelKey) => void;
  compact?: boolean;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  compact = false
}) => {
  const selectedOption = MODELS.find(m => m.id === selectedModel) || MODELS[0];

  if (compact) {
    return (
      <div className="relative inline-block">
        <select
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value as ModelKey)}
          className="appearance-none border rounded-lg 
                   px-3 py-1.5 pr-8 text-xs cursor-pointer
                   focus:border-sky-500 focus:outline-none
                   transition-colors theme-transition"
          style={{ 
            backgroundColor: 'var(--color-bg-secondary)', 
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)'
          }}
        >
          {MODELS.map(model => (
            <option key={model.id} value={model.id} style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-primary)' }}>
              {model.name} {model.supportsImages ? '📷' : ''}
            </option>
          ))}
        </select>
        <span className="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-sm pointer-events-none opacity-50" style={{ color: 'var(--color-text-secondary)' }}>
          expand_more
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium uppercase tracking-wide opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
        AI Model
      </label>
      <div className="grid grid-cols-2 gap-2">
        {MODELS.map(model => (
          <button
            key={model.id}
            onClick={() => onModelChange(model.id)}
            className={`
              relative p-3 rounded-lg border text-left transition-all
              ${selectedModel === model.id
                ? 'border-sky-500 bg-sky-500/10'
                : 'hover:opacity-80'
              }
            `}
            style={selectedModel === model.id ? {} : { 
              backgroundColor: 'var(--color-bg-secondary)', 
              borderColor: 'var(--color-border)' 
            }}
          >
            <div className="flex items-start gap-2">
              <span className={`material-symbols-outlined text-lg ${
                selectedModel === model.id ? 'text-sky-500' : 'opacity-40'
              }`} style={selectedModel === model.id ? {} : { color: 'var(--color-text-primary)' }}>
                {model.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                    {model.name}
                  </span>
                  {model.supportsImages && (
                    <span className="text-[10px] px-1 py-0.5 bg-emerald-500/20 text-emerald-500 rounded">
                      IMG
                    </span>
                  )}
                </div>
                <p className="text-[10px] mt-0.5 opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                  {model.description}
                </p>
              </div>
            </div>
            
            {selectedModel === model.id && (
              <span className="absolute top-1.5 right-1.5 material-symbols-outlined text-sky-500 text-sm">
                check_circle
              </span>
            )}
          </button>
        ))}
      </div>
      
      {/* Selected Model Info */}
      <div className="flex items-center gap-2 p-2 rounded text-[10px] opacity-60" style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }}>
        <span className="material-symbols-outlined text-sm">info</span>
        <span>
          {selectedOption.supportsImages 
            ? 'This model supports medical image analysis (X-ray, dermoscopy, pathology)'
            : 'Text-only model - switch to a multimodal model for image support'
          }
        </span>
      </div>
    </div>
  );
};

export default ModelSelector;

// Helper to check if current model supports images
export const modelSupportsImages = (modelKey: ModelKey): boolean => {
  const model = MODELS.find(m => m.id === modelKey);
  return model?.supportsImages ?? false;
};
