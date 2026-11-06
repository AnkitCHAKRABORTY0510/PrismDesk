import api from "./api";
import { cleanParams, type MessageResponse, type Page, type QueryParams } from "./types";

export type NotificationCategory = "tasks" | "projects" | "research" | "conferences" | "handbook" | "administrative";
export type NotificationStatus = "pending" | "processing" | "sent" | "failed" | "retry_scheduled";

export interface DiscordStatus {
  linked: boolean;
  discord_username: string | null;
  linked_at: string | null;
  oauth_configured: boolean;
  bot_configured: boolean;
}

export interface Preference {
  category: NotificationCategory;
  enabled: boolean;
}

export interface NotificationRecord {
  id: string;
  recipient_id: string | null;
  channel_id: string | null;
  category: NotificationCategory;
  event_type: string;
  title: string;
  body: string;
  status: NotificationStatus;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at: string;
  last_attempt_at: string | null;
  sent_at: string | null;
  last_error: string | null;
  created_at: string;
}

const base = "/api/v1/notifications";

export const discordStatus = async () => (await api.get<DiscordStatus>(`${base}/discord`)).data;
export const startDiscordLink = async () =>
  (await api.post<{ authorize_url: string }>(`${base}/discord/link`)).data;
export const unlinkDiscord = async () => (await api.delete<MessageResponse>(`${base}/discord`)).data;
export const getPreferences = async () => (await api.get<Preference[]>(`${base}/preferences`)).data;
export const savePreferences = async (preferences: Preference[]) =>
  (await api.put<Preference[]>(`${base}/preferences`, { preferences })).data;
export const myNotifications = async (params: QueryParams = {}) =>
  (await api.get<Page<NotificationRecord>>(`${base}/history`, { params: cleanParams(params) })).data;
export const notificationQueue = async (params: QueryParams = {}) =>
  (await api.get<Page<NotificationRecord>>(`${base}/queue`, { params: cleanParams(params) })).data;
export const retryNotification = async (id: string) =>
  (await api.post<NotificationRecord>(`${base}/${id}/retry`)).data;
export const sendAnnouncement = async (input: {
  title: string;
  body: string;
  post_to_channel: boolean;
  direct_message_all: boolean;
}) => (await api.post<{ queued: number; channel_configured: boolean }>(`${base}/announcements`, input)).data;
