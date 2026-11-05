import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DecisionLabel } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { RiskComposition } from "../components/RiskComposition";
import { InvestigationPage } from "../pages/Investigation";
import { mockFetch, renderAt, summary } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("DecisionBadge", () => {
  it.each<DecisionLabel>(["Permitted", "Needs verification", "Preventive risk block", "Confirmed fraud evidence"])(
    "always shows the %s label as text",
    (label) => {
      render(<DecisionBadge label={label} />);
      expect(screen.getByText(label)).toBeInTheDocument();
    },
  );
});

describe("RiskComposition", () => {
  it("states the weighted arithmetic and thresholds", () => {
    render(
      <RiskComposition
        total={42}
        verify={61}
        block={97}
        details={[
          { key: "isolation_forest", label: "Isolation Forest", score: 0.2, weight: 0.35, contribution: 7, raw: null, status: null, detail: "" },
          { key: "lof", label: "Local Outlier Factor", score: 0.4, weight: 0.25, contribution: 10, raw: null, status: null, detail: "" },
          { key: "dbscan", label: "DBSCAN context", score: 1, weight: 0.1, contribution: 10, raw: null, status: null, detail: "" },
          { key: "rules", label: "Behaviour rules", score: 0.5, weight: 0.3, contribution: 15, raw: null, status: null, detail: "" },
        ]}
      />,
    );
    expect(screen.getByRole("img", { name: /Risk 42.0 of 100/ })).toBeInTheDocument();
    expect(screen.getByText(/not a probability of fraud/)).toBeInTheDocument();
    expect(screen.getByText("15.0")).toBeInTheDocument();
  });
});

describe("Investigation review", () => {
  it("requires a reason and keeps the original decision visible", async () => {
    const assessment = {
      ...summary("REQ-1", 1, { decision: "Verify", decision_label: "Needs verification", outcome: "pending_verification", review_status: "pending", risk_score: 72.5 }),
      explanation: "Needs verification: unusual behaviour above the verification threshold.", status_notes: [], component_details: [],
      reasons: [], evidence: [], thresholds: { verify: 61, block: 97, min_corroborating_families: 2, source: "validated" },
      model_version: "m", policy_version: "p", operating_point_version: "o", assessed_at: "2026-10-28T10:00:00Z",
      device_id: "D", session_id: "S", auth_method: "biometric", ip_country: "DE", channel: "mobile_app", facts: {}, idempotent_replay: false,
    };
    const calls = mockFetch((url) => {
      if (url.endsWith("/reviews")) return { status: 201, body: { assessment, timeline: [], reviews: [], can_review: false } };
      return { body: { assessment, timeline: [], reviews: [], can_review: true } };
    });
    renderAt(<InvestigationPage />, "/investigations/REQ-1", "/investigations/:requestId");
    expect(await screen.findByText(/unusual behaviour above the verification threshold/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve payment" }));
    expect(screen.getByRole("radio", { name: "Approve" })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByText(/at least 8 characters/)).toBeInTheDocument();
    expect(calls.some((c) => c.url.endsWith("/reviews"))).toBe(false);
    await userEvent.type(screen.getByLabelText(/Reason/), "Customer confirmed the payee by phone");
    await userEvent.click(screen.getByRole("button", { name: "Approve payment" }));
    const post = calls.find((c) => c.url.endsWith("/reviews"));
    expect(post && JSON.parse(String(post.init?.body))).toMatchObject({ action: "approve", reason: "Customer confirmed the payee by phone" });
  });
});
