/**
 * Browser Push Notifications — Web Notification API (nativa, fara service worker).
 * Necesita permisiune utilizator, activata din Settings.
 */

export async function requestNotificationPermission(): Promise<boolean> {
  if (!("Notification" in window)) return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  const result = await Notification.requestPermission();
  return result === "granted";
}

export function sendBrowserNotification(
  title: string,
  body: string,
  url?: string
): void {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const n = new Notification(title, {
    body,
    icon: "/favicon.ico",
    tag: "ris-notification",
    requireInteraction: false,
  });
  if (url) {
    n.onclick = () => {
      window.focus();
      window.location.href = url;
      n.close();
    };
  }
  // Auto-close dupa 5 secunde
  setTimeout(() => n.close(), 5000);
}

export function isNotificationSupported(): boolean {
  return "Notification" in window;
}

export function getNotificationPermission(): NotificationPermission | "unsupported" {
  if (!("Notification" in window)) return "unsupported";
  return Notification.permission;
}
