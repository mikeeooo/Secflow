import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SimulatorPage } from "../pages/Simulator";
import { mockFetch, renderAt, summary } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const options = {
  simulation_time: "2026-10-28T10:00:00Z", currencies: ["EUR"], auth_methods: ["biometric"], countries: ["DE", "US"],
  flagged_beneficiaries: [],
  sender: { account_id: "ACC-0001", home_country: "DE", known_devices: ["DEV-0001-A"], recent_recipients: [{ id: "CP-00001", name: "Harbor Lane Utilities", kind: "counterparty" }], median_amount: 40 },
};
const detail = {
  ...summary("SIM-x", 11), explanation: "Permitted: risk 31.2 is below the verification threshold 61.", status_notes: [],
  component_details: [], reasons: [], evidence: [], thresholds: { verify: 61, block: 97, min_corroborating_families: 2, source: "validated" },
  model_version: "m", policy_version: "p", operating_point_version: "o", assessed_at: "2026-10-28T10:00:00Z",
  device_id: "DEV-0001-A", session_id: "S", auth_method: "biometric", ip_country: "DE", channel: "mobile_app", facts: {}, idempotent_replay: false,
};

function baseHandler(simulate: (body: Record<string, unknown>) => { status?: number; body?: unknown }) {
  return mockFetch((url, init) => {
    if (url.startsWith("/api/parties")) return { body: [{ id: "ACC-0001", name: "Amara Okafor", kind: "account", detail: "personal" }] };
    if (url.startsWith("/api/simulator/options")) return { body: options };
    if (url === "/api/simulations") return simulate(JSON.parse(String(init?.body)));
    return { body: {} };
  });
}

describe("Payment Simulator", () => {
  it("does not submit anything on load (a refresh cannot resubmit)", async () => {
    const calls = baseHandler(() => ({ status: 201, body: detail }));
    renderAt(<SimulatorPage />);
    await screen.findByDisplayValue("Amara Okafor");
    expect(calls.filter((c) => c.url === "/api/simulations")).toHaveLength(0);
  });

  it("validates required fields before sending", async () => {
    const calls = baseHandler(() => ({ status: 201, body: detail }));
    renderAt(<SimulatorPage />);
    await screen.findByDisplayValue("Amara Okafor");
    await userEvent.click(screen.getByRole("button", { name: "Submit for assessment" }));
    expect(await screen.findByText("Enter an amount greater than zero.")).toBeInTheDocument();
    expect(screen.getByText(/Choose a recipient/)).toBeInTheDocument();
    expect(calls.filter((c) => c.url === "/api/simulations")).toHaveLength(0);
  });

  it("retries a failed submission with the same request ID, then uses a new ID", async () => {
    const ids: string[] = [];
    let attempt = 0;
    baseHandler((body) => {
      ids.push(String(body.request_id));
      attempt += 1;
      return attempt === 1 ? { status: 0 } : { status: 201, body: detail };
    });
    renderAt(<SimulatorPage />);
    await screen.findByDisplayValue("Amara Okafor");
    await userEvent.click(await screen.findByRole("button", { name: /Ordinary payment/ }));
    await userEvent.click(screen.getByRole("button", { name: "Submit for assessment" }));
    await userEvent.click(await screen.findByRole("button", { name: /Retry same request/ }));
    expect(await screen.findByText(/below the verification threshold/)).toBeInTheDocument();
    expect(ids).toHaveLength(2);
    expect(ids[0]).toBe(ids[1]);
    await waitFor(() => expect(screen.getByText(/^Request ID /).textContent).not.toContain(ids[0]));
    expect(screen.getByRole("link", { name: /Open investigation/ })).toHaveAttribute("href", "/investigations/SIM-x");
  });
});
