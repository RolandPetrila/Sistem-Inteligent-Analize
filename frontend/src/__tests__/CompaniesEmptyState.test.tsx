/**
 * Regression test — link-ul din empty-state al paginii Companii ("Porneste
 * analiza") tintea `/new`, o ruta INEXISTENTA (App.tsx declara `/new-analysis`),
 * deci cadea pe pagina NotFound (404). Test separat de Companies.test.tsx
 * (fisier cu hang preexistent confirmat — vezi CLAUDE.md/memory — nu se atinge).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/api", () => ({
  api: {
    listCompanies: vi.fn(() => Promise.resolve({ companies: [], total: 0 })),
    listFavorites: vi.fn(() => Promise.resolve({ companies: [], total: 0 })),
    exportCompaniesCSV: vi.fn(),
    toggleFavorite: vi.fn(() => Promise.resolve({ is_favorite: false })),
  },
}));

vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/lib/logger", () => ({
  logAction: vi.fn(),
}));

vi.mock("@/hooks/useDebounce", () => ({
  useDebounce: (val: unknown) => val,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

describe("Companies — empty state link", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("linkul 'Porneste analiza' tinteste /new-analysis (ruta reala din App.tsx), nu /new", async () => {
    const queryClient = createTestQueryClient();
    const { default: Companies } = await import("../pages/Companies");
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Companies />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const link = await waitFor(() =>
      screen.getByRole("link", { name: /Porneste analiza/i }),
    );
    expect(link).toHaveAttribute("href", "/new-analysis");
  });
});
