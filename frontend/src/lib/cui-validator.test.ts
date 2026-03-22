import { describe, it, expect } from "vitest";
import { validateCUI } from "./cui-validator";

describe("validateCUI", () => {
  it("validates MOSSLEIN CUI correctly", () => {
    const result = validateCUI("26313362");
    expect(result.valid).toBe(true);
    expect(result.cui).toBe("26313362");
  });

  it("accepts RO prefix", () => {
    const result = validateCUI("RO26313362");
    expect(result.valid).toBe(true);
    expect(result.cui).toBe("26313362");
  });

  it("trims whitespace", () => {
    const result = validateCUI("  26313362  ");
    expect(result.valid).toBe(true);
  });

  it("validates Bitdefender CUI", () => {
    const result = validateCUI("18189442");
    expect(result.valid).toBe(true);
  });

  it("rejects wrong check digit", () => {
    const result = validateCUI("26313363");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("Cifra de control");
  });

  it("rejects empty input", () => {
    const result = validateCUI("");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("gol");
  });

  it("rejects non-numeric characters", () => {
    const result = validateCUI("ABC123");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("cifre");
  });

  it("rejects too short CUI", () => {
    const result = validateCUI("1");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("2-10");
  });

  it("rejects too long CUI", () => {
    const result = validateCUI("12345678901");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("2-10");
  });

  it("handles lowercase ro prefix", () => {
    const result = validateCUI("ro26313362");
    expect(result.valid).toBe(true);
  });

  it("matches backend validation for same CUI", () => {
    // These CUIs should produce the same valid/invalid result as the Python backend
    const testCases = [
      { cui: "26313362", expected: true },
      { cui: "18189442", expected: true },
      { cui: "26313363", expected: false },
      { cui: "12345679", expected: false },
    ];

    for (const tc of testCases) {
      const result = validateCUI(tc.cui);
      expect(result.valid).toBe(tc.expected);
    }
  });
});
