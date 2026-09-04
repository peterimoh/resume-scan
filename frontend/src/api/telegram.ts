import { api } from "./client";

export interface TelegramConnect {
  deep_link: string;
  expires_at: string;
}

export interface TelegramStatus {
  linked: boolean;
  chat_id: string | null;
  username: string | null;
}

export const telegramApi = {
  createConnectToken: () => api.post<TelegramConnect>("/api/telegram/connect-token"),
  status: () => api.get<TelegramStatus>("/api/telegram/status"),
  unlink: () => api.delete<void>("/api/telegram/link"),
};
