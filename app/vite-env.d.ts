/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_LOCAL_BACKEND?: string;
  readonly VITE_BACKEND_URL?: string;
  readonly VITE_GOOGLE_API_KEY?: string;
  readonly VITE_API_KEY?: string;
  readonly VITE_GOOGLE_MODEL_ID?: string;
  readonly VITE_MEDGEMMA_4B_MODEL_ID?: string;
  readonly VITE_MEDGEMMA_27B_TEXT_MODEL_ID?: string;
  readonly VITE_MEDGEMMA_27B_MM_MODEL_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
