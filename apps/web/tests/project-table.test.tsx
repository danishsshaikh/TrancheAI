import { render, screen } from "@testing-library/react";
import { ProjectTable } from "../src/features/projects/ProjectTable";
import { demoProjects } from "../src/api/client";

test("renders project list data", () => {
  render(<ProjectTable projects={demoProjects} canEdit />);
  expect(screen.getByText("SP-001")).toBeInTheDocument();
  expect(screen.getByText("Synthetic Assistive Mobility Prototype")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
});

test("renders empty state", () => {
  render(<ProjectTable projects={[]} />);
  expect(screen.getByText("No projects match the current filters.")).toBeInTheDocument();
});

