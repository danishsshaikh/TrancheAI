import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AIAssistantPage } from "../src/pages/AiAssistantPage";
import { ProjectsPage } from "../src/pages/ProjectsPage";
import { ReconciliationPage } from "../src/pages/ReconciliationPage";
import { TrancheFormPage } from "../src/pages/TrancheFormPage";

function renderPage(page: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("TrancheAI administrative UI", () => {
  it("renders and filters the project list", async () => {
    renderPage(<ProjectsPage />);
    expect(screen.getByText("SP-001")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/Search by code/), "mobility");
    expect(screen.getByText("Synthetic Assistive Mobility Prototype")).toBeInTheDocument();
  });

  it("shows tranche client-side validation", async () => {
    renderPage(<TrancheFormPage />);
    await userEvent.clear(screen.getByLabelText("Approved Amount"));
    await userEvent.type(screen.getByLabelText("Approved Amount"), "999999");
    await userEvent.click(screen.getByRole("button", { name: /Save Draft/ }));
    expect(await screen.findByText("Approved amount cannot exceed requested amount.")).toBeInTheDocument();
  });

  it("renders reconciliation issue details", async () => {
    renderPage(<ReconciliationPage />);
    expect(await screen.findByText("missing_payment_reference")).toBeInTheDocument();
    expect(screen.getByText(/missing a payment reference/)).toBeInTheDocument();
  });

  it("renders AI proposal preview", async () => {
    renderPage(<AIAssistantPage />);
    expect(await screen.findByText("Action Preview")).toBeInTheDocument();
    expect(screen.getByText("propose_tranche_creation")).toBeInTheDocument();
  });
});

