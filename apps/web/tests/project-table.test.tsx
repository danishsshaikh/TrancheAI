import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";
import { ProjectTable } from "../src/features/projects/ProjectTable";
import type { ProjectRow } from "../src/types/domain";

const projects: ProjectRow[] = [{
  id: "project-1",
  projectCode: "SP-001",
  title: "Synthetic Assistive Mobility Prototype",
  school: "School of Engineering",
  department: "Robotics",
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
}];

function renderTable(projectRows: ProjectRow[], canEdit = false) {
  return render(
    <MemoryRouter>
      <ProjectTable projects={projectRows} canEdit={canEdit} />
    </MemoryRouter>
  );
}

test("renders project list data", () => {
  renderTable(projects, true);
  expect(screen.getByText("SP-001")).toBeInTheDocument();
  expect(screen.getByText("Synthetic Assistive Mobility Prototype")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
});

test("renders empty state", () => {
  renderTable([]);
  expect(screen.getByText("No projects match the current filters.")).toBeInTheDocument();
});
