import { useState } from "react";
import { Mail, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { logAction } from "@/lib/logger";

interface EmailModalProps {
  open: boolean;
  onClose: () => void;
  reportId: string;
  initialSubject: string;
}

export function EmailModal({
  open,
  onClose,
  reportId,
  initialSubject,
}: EmailModalProps) {
  const { toast } = useToast();
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState(initialSubject);
  const [emailMessage, setEmailMessage] = useState("");
  const [sending, setSending] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailTo.trim()) {
      toast("Introdu adresa de email", "warning");
      return;
    }
    setSending(true);
    try {
      await api.sendReportEmail(reportId, {
        to: emailTo.trim(),
        subject: emailSubject,
        message: emailMessage,
      });
      toast("Email trimis cu succes!", "success");
      logAction("ReportView", "sendEmail", { reportId, to: emailTo });
      onClose();
      setEmailTo("");
      setEmailMessage("");
    } catch {
      toast(
        "Eroare la trimiterea emailului. Verifica configurarea Gmail.",
        "error",
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-[61] flex items-center justify-center p-4">
        <div className="bg-dark-card border border-dark-border rounded-xl shadow-2xl w-full max-w-md">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-border">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Mail className="w-4 h-4 text-accent-secondary" />
              Trimite raport pe email
            </h3>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">
                Destinatar
              </label>
              <input
                type="email"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                placeholder="email@exemplu.com"
                className="input-field w-full"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">
                Subiect
              </label>
              <input
                type="text"
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
                className="input-field w-full"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">
                Mesaj (optional)
              </label>
              <textarea
                value={emailMessage}
                onChange={(e) => setEmailMessage(e.target.value)}
                placeholder="Mesaj aditional..."
                rows={3}
                className="input-field w-full resize-none"
              />
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={sending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {sending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Se trimite...
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    Trimite
                  </>
                )}
              </button>
              <button type="button" onClick={onClose} className="btn-secondary">
                Anuleaza
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
