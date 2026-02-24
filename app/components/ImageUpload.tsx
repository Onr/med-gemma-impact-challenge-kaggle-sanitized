import React, { useState, useRef, useCallback } from 'react';

export interface ImageData {
  id: string;
  file: File;
  preview: string;
  mimeType: string;
  base64?: string;
}

interface ImageUploadProps {
  onImagesChange: (images: ImageData[]) => void;
  maxImages?: number;
  disabled?: boolean;
}

const ImageUpload: React.FC<ImageUploadProps> = ({
  onImagesChange,
  maxImages = 4,
  disabled = false
}) => {
  const [images, setImages] = useState<ImageData[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const validFiles = fileArray.filter(f => 
      f.type.startsWith('image/') && f.size < 10 * 1024 * 1024 // 10MB limit
    );

    const newImages: ImageData[] = [];
    
    for (const file of validFiles.slice(0, maxImages - images.length)) {
      const preview = URL.createObjectURL(file);
      
      // Convert to base64
      const base64 = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          resolve(result.split(',')[1]); // Remove data URL prefix
        };
        reader.readAsDataURL(file);
      });

      newImages.push({
        id: `img-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        file,
        preview,
        mimeType: file.type,
        base64
      });
    }

    const updatedImages = [...images, ...newImages].slice(0, maxImages);
    setImages(updatedImages);
    onImagesChange(updatedImages);
  }, [images, maxImages, onImagesChange]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!disabled && e.dataTransfer.files.length) {
      processFiles(e.dataTransfer.files);
    }
  }, [disabled, processFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      processFiles(e.target.files);
    }
  }, [processFiles]);

  const removeImage = useCallback((id: string) => {
    const updated = images.filter(img => img.id !== id);
    // Revoke the preview URL to free memory
    const removed = images.find(img => img.id === id);
    if (removed) {
      URL.revokeObjectURL(removed.preview);
    }
    setImages(updated);
    onImagesChange(updated);
  }, [images, onImagesChange]);

  const clearAll = useCallback(() => {
    images.forEach(img => URL.revokeObjectURL(img.preview));
    setImages([]);
    onImagesChange([]);
  }, [images, onImagesChange]);

  if (disabled) return null;

  return (
    <div className="space-y-2 theme-transition">
      {/* Image Previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 p-2 rounded-lg" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          {images.map(img => (
            <div 
              key={img.id} 
              className="relative group w-16 h-16 rounded-lg overflow-hidden border"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <img 
                src={img.preview} 
                alt="Upload preview" 
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => removeImage(img.id)}
                className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 
                           flex items-center justify-center transition-opacity"
                title="Remove image"
              >
                <span className="material-symbols-outlined text-red-400 text-lg">
                  close
                </span>
              </button>
            </div>
          ))}
          
          {images.length > 1 && (
            <button
              onClick={clearAll}
              className="w-16 h-16 rounded-lg border border-dashed flex flex-col items-center justify-center opacity-60 hover:opacity-100 hover:text-red-400 hover:border-red-400 transition-all"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
              title="Clear all"
            >
              <span className="material-symbols-outlined text-sm">delete</span>
              <span className="text-[8px] mt-0.5">Clear all</span>
            </button>
          )}
        </div>
      )}

      {/* Upload Area */}
      {images.length < maxImages && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`
            flex items-center gap-2 p-2 rounded-lg border border-dashed cursor-pointer
            transition-all duration-200 theme-transition
            ${isDragging 
              ? 'border-sky-500 bg-sky-500/10' 
              : 'hover:opacity-80'
            }
          `}
          style={isDragging ? {} : { 
            borderColor: 'var(--color-border)', 
            backgroundColor: 'var(--color-bg-input)' 
          }}
        >
          <span className={`material-symbols-outlined text-lg ${isDragging ? 'text-sky-500' : 'opacity-40'}`} style={isDragging ? {} : { color: 'var(--color-text-primary)' }}>
            add_photo_alternate
          </span>
          <span className="text-xs opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
            {isDragging ? 'Drop image here' : `Add medical image (${images.length}/${maxImages})`}
          </span>
          
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      )}

      {/* Image Type Hints */}
      {images.length === 0 && (
        <div className="flex flex-wrap gap-1 text-[10px]">
          {['X-ray', 'Dermoscopy', 'Pathology', 'CT/MRI'].map(hint => (
            <span key={hint} className="px-1.5 py-0.5 rounded opacity-60" style={{ backgroundColor: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }}>
              {hint}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default ImageUpload;
