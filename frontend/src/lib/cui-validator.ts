/**
 * Validare CUI Romania — cifra de control MOD 11.
 * Identic cu backend/agents/tools/cui_validator.py.
 */
const WEIGHTS = [7, 5, 3, 2, 1, 7, 5, 3, 2];

export function validateCUI(input: string): {
  valid: boolean;
  cui: string;
  error?: string;
} {
  // Cleanup
  let cui = input.trim().toUpperCase().replace(/^RO/, "").replace(/\s/g, "");

  if (!cui) return { valid: false, cui: "", error: "CUI gol" };
  if (!/^\d+$/.test(cui)) return { valid: false, cui, error: "CUI trebuie sa contina doar cifre" };
  if (cui.length < 2 || cui.length > 10)
    return { valid: false, cui, error: "CUI trebuie sa aiba 2-10 cifre" };

  // Cifra de control (ultima cifra)
  const checkDigit = parseInt(cui[cui.length - 1], 10);
  const body = cui.slice(0, -1).padStart(9, "0");

  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(body[i], 10) * WEIGHTS[i];
  }

  const remainder = (sum * 10) % 11;
  const expected = remainder === 10 ? 0 : remainder;

  if (checkDigit !== expected) {
    return {
      valid: false,
      cui,
      error: `Cifra de control invalida (asteptat ${expected}, primit ${checkDigit})`,
    };
  }

  return { valid: true, cui };
}
