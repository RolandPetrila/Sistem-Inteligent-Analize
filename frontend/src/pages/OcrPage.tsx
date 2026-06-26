import { useState } from "react";
import { FileText, Upload, Loader2, FileSearch, Copy } from "lucide-react";
import clsx from "clsx";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { logAction } from "@/lib/logger";

// Stays in sync with api.ts ocrDocument return shape:
// { filename, type, pages, text, char_count, model }
type OcrResult = Awaited<ReturnType<typeof api.ocrDocument>>;

export default function OcrPage() {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OcrResult | null>(null);

  const handleExtract = async () => {
    if (!file || loading) return;
    setLoading(true);
    setResult(null);
    logAction("OcrPage", "ocr_extract", {
      fileName: file.name,
      size: file.size,
      type: file.type,
    });

    try {
      const data = await api.ocrDocument(file);
      setResult(data);
      toast(
        `Text extras: ${data.char_count.toLocaleString("ro-RO")} caractere`,
        "success",
      );
    } catch (err) {
      toast(
        err instanceof Error
          ? err.message
          : "Eroare la extragerea textului (OCR)",
        "error",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result?.text) return;
    try {
      await navigator.clipboard.writeText(result.text);
      toast("Text copiat in clipboard", "success");
    } catch {
      toast("Nu s-a putut copia textul", "error");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-accent-primary" />
          OCR Documente (Mistral)
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Extrage textul din PDF-uri si imagini folosind serviciul Mistral OCR
        </p>
      </div>

      {/* Upload + Action */}
      <div className="card max-w-xl space-y-4">
        <div
          className={clsx(
            "border-2 border-dashed rounded-xl p-8 text-center transition-colors",
            file
              ? "border-accent-primary/50 bg-accent-primary/5"
              : "border-dark-border",
          )}
        >
          <Upload className="w-10 h-10 text-gray-500 mx-auto mb-3" />
          <p className="text-sm text-gray-400 mb-3">
            {file
              ? file.name
              : "Selecteaza un PDF sau o imagine pentru extragere OCR"}
          </p>
          <input
            type="file"
            accept=".pdf,application/pdf,image/*"
            className="hidden"
            id="ocr-upload"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              setResult(null);
            }}
          />
          <label
            htmlFor="ocr-upload"
            className="btn-secondary cursor-pointer inline-block"
          >
            {file ? "Schimba fisier" : "Alege fisier"}
          </label>
        </div>

        <p className="text-xs text-gray-600">
          Formate acceptate: PDF, PNG, JPG, JPEG, WEBP. Documentul este trimis
          catre serviciul Mistral OCR pentru recunoasterea textului.
        </p>

        <button
          onClick={handleExtract}
          disabled={!file || loading}
          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Se proceseaza OCR...
            </>
          ) : (
            <>
              <FileSearch className="w-4 h-4" /> Extrage text (OCR)
            </>
          )}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="card space-y-4">
          {/* Metadata */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetaCard label="Fisier" value={result.filename} />
            <MetaCard label="Pagini" value={String(result.pages)} />
            <MetaCard
              label="Caractere"
              value={result.char_count.toLocaleString("ro-RO")}
            />
            <MetaCard label="Model" value={result.model} />
          </div>

          {/* Extracted text */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                Text extras
              </h2>
              <button
                onClick={handleCopy}
                disabled={!result.text}
                className="btn-secondary flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Copy className="w-3.5 h-3.5" /> Copiaza text
              </button>
            </div>
            <textarea
              readOnly
              value={result.text}
              aria-label="Text extras prin OCR"
              className="w-full h-96 bg-dark-surface border border-dark-border rounded-lg p-3 text-xs font-mono text-gray-300 leading-relaxed resize-none overflow-auto focus:outline-none focus:ring-1 focus:ring-accent-primary"
            />
            {!result.text && (
              <p className="text-xs text-gray-600 mt-2">
                Nu s-a extras niciun text din acest document.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 bg-dark-surface rounded-lg">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider">
        {label}
      </p>
      <p
        className="text-sm text-gray-200 font-medium truncate mt-0.5"
        title={value}
      >
        {value}
      </p>
    </div>
  );
}
