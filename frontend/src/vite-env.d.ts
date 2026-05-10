/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CHAT_ACCESS_CODE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
