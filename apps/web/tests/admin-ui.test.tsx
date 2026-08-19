import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../src/app/AuthContext";
import { Layout } from "../src/components/Layout";
import { AiAssistantPage } from "../src/pages/AiAssistantPage";
import { ImportsExportsPage } from "../src/pages/ImportsExportsPage";
import { ProjectDetailPage } from "../src/pages/ProjectDetailPage";
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
  version: 1,
  summary: {
    totalSanctionedAmount: "500000.00",
    netDisbursedAmount: "100000.00",
    availableSanctionedBalance: "400000.00",
    pendingApprovedAmount: "0.00",
    trancheCount: 1,
    reconciliationStatus: "balanced",
  },
};

const projectDetail = {
  ...project,
  sanctions: [],
  fundingRevisions: [],
  tranches: [],
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

const importBatch = {
  id: "batch-1",
  importType: "projects",
  filename: "projects.csv",
  status: "previewed",
  rowsDetected: 1,
  validRows: 1,
  invalidRows: 0,
  duplicateRows: 0,
  existingRecordsMatched: 0,
  proposedCreates: 1,
  proposedUpdates: 0,
  committedRows: 0,
  failedRows: 0,
  skippedRows: 0,
  rows: [{
    id: "row-1",
    rowNumber: 2,
    status: "valid",
    proposedAction: "create",
    duplicate: false,
    entityType: "project",
    entityId: null,
    existingEntityId: null,
    errors: [],
    warnings: [],
    rawValues: { project_code: "TRAI-UI-001" },
    normalizedValues: { project_code: "TRAI-UI-001" },
    result: {},
  }],
};

function json(data: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }));
}

beforeEach(() => {
  localStorage.setItem("trancheai.auth", "test-token");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/v1/auth/me")) {
      return json({ id: "user-1", email: "admin@example.test", fullName: "Admin User", role: "administrator" });
    }
    if (url.includes("/api/v1/ai/proposals/proposal-1/confirm")) {
      return json({ kind: "result", message: "AI proposal executed.", proposal: aiProposal("executed"), data: { projectCode: "SP-777" } });
    }
    if (url.includes("/api/v1/ai/proposals/proposal-1/cancel")) {
      return json({ kind: "result", message: "Proposal cancelled.", proposal: aiProposal("cancelled") });
    }
    if (url.includes("/api/v1/ai/requests")) {
      const body = typeof init?.body === "string" ? JSON.parse(init.body) as { text?: string } : {};
      if (body.text?.includes("disabled")) {
        return json({ kind: "error", message: "AI assistant is disabled. Set AI_ENABLED=true on the server to use it." });
      }
      if (body.text?.includes("proposal")) {
        return json({ kind: "proposal", message: "Create project proposal ready.", proposal: aiProposal("pending_confirmation") });
      }
      if (body.text?.includes("export")) {
        return json({ kind: "export", message: "Generated project master export link.", download_url: "/api/v1/exports/project-master.csv" });
      }
      if (body.text?.includes("मराठी")) {
        return json({ kind: "answer", message: "मराठी प्रतिसाद", data: { projectCode: "SP-001", status: "balanced" } });
      }
      return json({ kind: "answer", message: "Found 1 matching project.", data: [{ projectCode: "SP-001", title: project.title, status: "active" }] });
    }
    if (url.includes("/api/v1/projects/project-1/audit")) {
      return json([]);
    }
    if (url.includes("/api/v1/projects/project-1")) {
      return json(projectDetail);
    }
    if (url.includes("/api/v1/projects?")) {
      return json([project]);
    }
    if (url.includes("/api/v1/reports/reconciliation")) {
      return json([issue]);
    }
    if (url.includes("/api/v1/imports/preview")) {
      return json(importBatch);
    }
    if (url.includes("/api/v1/imports/batch-1/commit")) {
      return json({ ...importBatch, status: "committed", committedRows: 1, proposedCreates: 0, rows: [{ ...importBatch.rows[0], status: "committed", result: { status: "committed" } }] });
    }
    return json({ detail: "Not found" }, 404);
  }));
});

function renderPage(page: ReactElement, initialEntries: string[] = ["/"]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>{page}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function aiProposal(status: string) {
  return {
    id: "proposal-1",
    action: "create_project",
    status,
    targetEntityType: "project",
    targetEntityId: null,
    currentValues: {},
    proposedValues: { project_code: "SP-777", title: "AI Proposed Project", department: "Robotics" },
    validationResult: { valid: true, warnings: [], errors: [] },
    message: "Create project proposal ready.",
    expiresAt: new Date(Date.now() + 900000).toISOString(),
    result: status === "executed" ? { projectCode: "SP-777" } : {},
  };
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

  it("previews and commits an import batch", async () => {
    renderPage(<ImportsExportsPage />);
    const file = new File(["project_code,project_title\nTRAI-UI-001,UI import\n"], "projects.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("CSV File"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /Preview/ }));
    expect(await screen.findByText("TRAI-UI-001")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Commit" }));
    expect(await screen.findByText("committed")).toBeInTheDocument();
  });

  it("includes the AI assistant in the main navigation", async () => {
    renderPage(<Layout><div>Current page</div></Layout>);
    expect(await screen.findByText("AI Assistant")).toBeInTheDocument();
  });

  it("renders AI answers with Unicode text and structured data", async () => {
    renderPage(<AiAssistantPage />);
    fireEvent.change(screen.getByLabelText("AI request"), { target: { value: "मराठी summary" } });
    fireEvent.click(screen.getByRole("button", { name: "Send AI request" }));
    expect(await screen.findByText("मराठी प्रतिसाद")).toBeInTheDocument();
    expect(screen.getByText("SP-001")).toBeInTheDocument();
  });

  it("shows AI proposal confirmation and cancellation states", async () => {
    renderPage(<AiAssistantPage />);
    fireEvent.change(screen.getByLabelText("AI request"), { target: { value: "proposal create project" } });
    fireEvent.click(screen.getByRole("button", { name: "Send AI request" }));
    expect(await screen.findByText("Create project proposal ready.")).toBeInTheDocument();
    expect(screen.getByText("SP-777")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("AI proposal executed.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("AI request"), { target: { value: "proposal create project" } });
    fireEvent.click(screen.getByRole("button", { name: "Send AI request" }));
    expect(await screen.findAllByText("Create project proposal ready.")).not.toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(await screen.findByText("Proposal cancelled.")).toBeInTheDocument();
  });

  it("renders disabled AI provider responses without crashing", async () => {
    renderPage(<AiAssistantPage />);
    fireEvent.change(screen.getByLabelText("AI request"), { target: { value: "disabled please" } });
    fireEvent.click(screen.getByRole("button", { name: "Send AI request" }));
    expect(await screen.findByText(/AI assistant is disabled/)).toBeInTheDocument();
  });

  it("passes project context from project details into the assistant launch", async () => {
    renderPage(<Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes>, ["/projects/project-1"]);
    const link = await screen.findByRole("link", { name: /AI Assistant/ });
    expect(link).toHaveAttribute("href", "/ai?projectId=project-1&projectCode=SP-001");

    renderPage(<AiAssistantPage />, ["/ai?projectId=project-1&projectCode=SP-001"]);
    expect(screen.getByText("Summarize SP-001")).toBeInTheDocument();
  });
});
