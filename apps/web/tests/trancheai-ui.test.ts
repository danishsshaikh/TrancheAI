import { describe, expect, it } from "vitest";

import { labelize, money, moneyOrNotApplicable, safeText } from "../src/utils/format";

describe("TrancheAI UI formatting", () => {
  it("formats invalid money values without leaking NaN", () => {
    expect(money(undefined)).toBe("-");
    expect(money("not-a-number")).toBe("-");
    expect(moneyOrNotApplicable("not-a-number")).toBe("Not applicable");
  });

  it("turns internal statuses into human labels", () => {
    expect(labelize("missing_sanction")).toBe("Missing Sanction");
    expect(labelize("record-utilization")).toBe("Record Utilization");
  });

  it("uses explicit fallback text for empty fields", () => {
    expect(safeText("")).toBe("-");
    expect(safeText(null, "Not set")).toBe("Not set");
  });
});
