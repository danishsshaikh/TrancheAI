import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../src/app/AuthContext";
import { ProjectsPage } from "../src/pages/ProjectsPage";
import { ReconciliationPage } from "../src/pages/ReconciliationPage";
import { TrancheFormPage } from "../src/pages/TrancheFormPage";

const project = {
  id: "project-1",
  projectCode: "SP-001",
  title: "Synthetic Assistive Mobility Prototype",
  school: "School of Engineering",
  department: "Robotics",
  academicYear: "2025-26",
  status: "active",
  fundingStatus: "balanced",
  summary: {
    totalSanctionedAmount: "500000.00",
    netDisbursedAmount: "100000.00",
    availableSanctionedBalance: "400000.00",
    pendingApprovedAmount: "0.00",
    trancheCount: 1,
    reconciliationStatus: "balanced",
  },
};

const issue = {
  id: "issue-1",
  issueType: "missing_payment_reference",
  severity: "high",
  projectId: "project-1",
  projectCode: "SP-001",
  projectTitle: "Synthetic Assistive Mobility Prototype",
  description: "Tranche is missing a payment reference.",
  financialImpact: "100000.00",
  suggestedAction: "Record the payment reference.",
};

function json(data: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }));
}

beforeEach(() => {
  localStorage.setItem("trancheai.auth", "test-token");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return json({ id: "user-1", email: "admin@example.test", fullName: "Admin User", role: "administrator" });
    }
    if (url.includes("/api/v1/projects?")) {
      return json([project]);
    }
    if (url.includes("/api/v1/reports/reconciliation")) {
      return json([issue]);
    }
    return json({ detail: "Not found" }, 404);
  }));
});

function renderPage(page: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter>{page}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("TrancheAI administrative UI", () => {
  it("renders and filters the project list", async () => {
    renderPage(<ProjectsPage />);
    expect(await screen.findByText("SP-001")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/Search by code/), { target: { value: "mobility" } });
    expect(await screen.findByText("Synthetic Assistive Mobility Prototype")).toBeInTheDocument();
  });

  it("shows tranche client-side validation", async () => {
    renderPage(<TrancheFormPage />);
    expect(await screen.findByText("SP-001")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Approved Amount"), { target: { value: "999999" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Draft/ }));
    expect(await screen.findByText("Approved amount cannot exceed requested amount.")).toBeInTheDocument();
  });

  it("renders reconciliation issue details", async () => {
    renderPage(<ReconciliationPage />);
    expect(await screen.findByText("missing_payment_reference")).toBeInTheDocument();
    expect(screen.getByText(/missing a payment reference/)).toBeInTheDocument();
  });
});
