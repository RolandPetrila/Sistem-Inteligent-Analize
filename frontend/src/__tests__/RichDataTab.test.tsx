/**
 * CERINTA #4 (2026-07-26): linia de verificare manuala RNPM (co.rnpm.ro) apare
 * NECONDITIONAT in tabul RichDataTab -- auto-verificarea garantiilor reale mobiliare
 * (AEGRM) e structural moarta, deci portalul RNPM viu (co.rnpm.ro) e singura optiune
 * (scraping interzis: reCAPTCHA per-cautare).
 *
 * Non-vacuitate: pe HEAD, cu fullData gol, RichDataTab facea early-return cu doar
 * mesajul "Nu exista date extinse" -> niciun link co.rnpm.ro. Acest test PICA pe HEAD
 * (verificat prin swap richFields.ts + RichDataTab.tsx la HEAD -- vezi raportul).
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RichDataTab } from "@/components/report/RichDataTab";

function renderTab(fullData: Record<string, any> | null) {
  return render(
    <MemoryRouter>
      <RichDataTab fullData={fullData} />
    </MemoryRouter>,
  );
}

describe("RichDataTab — linia RNPM neconditionata", () => {
  it("randeaza linkul co.rnpm.ro chiar pe fullData gol (garantii.shown = false)", () => {
    const { container } = renderTab({});
    const link = container.querySelector('a[href="https://co.rnpm.ro"]');
    expect(link).not.toBeNull();
    expect(link?.textContent).toContain("co.rnpm.ro");
    // mesaj onest, NU "0 garantii" / "curat"
    expect(container.textContent).toContain(
      "verificare automata indisponibila",
    );
    expect(container.textContent?.toLowerCase()).not.toContain("0 garantii");
  });

  it("randeaza linkul co.rnpm.ro si cand alte sectiuni au date (calea principala)", () => {
    // sanctions prezent -> anyShown true -> corpul principal, unde GarantiiSection
    // se randeaza tot NECONDITIONAT.
    const { container } = renderTab({
      sanctions: { status: "clean", checked: ["X"], lists_checked: ["OFAC"] },
    });
    const link = container.querySelector('a[href="https://co.rnpm.ro"]');
    expect(link).not.toBeNull();
  });
});
