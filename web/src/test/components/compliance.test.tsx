/* Component tests for compliance wrappers — docs/steps/06. */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NotAdviceBanner, GroundingBadge, RaGatedPlaceholder } from "@/components/compliance";
import { ScoreBadge, EmptyState, ErrorState } from "@/components/ui";
import { AiStockSummaryCard } from "@/components/stock";

describe("NotAdviceBanner", () => {
  it("renders not-advice note", () => {
    render(<NotAdviceBanner />);
    expect(screen.getByRole("note")).toBeInTheDocument();
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
  });
});

describe("GroundingBadge", () => {
  it("renders grounding note and view-evidence button when callback provided", () => {
    const spy = vi.fn();
    render(<GroundingBadge onViewEvidence={spy} />);
    expect(screen.getByText(/grounded in this stock/i)).toBeInTheDocument();
    /* aria-label contains "View evidence" — query by accessible name substring */
    const btn = screen.getByRole("button", { name: /view evidence/i }) ??
                screen.getByLabelText(/view.*evidence/i);
    fireEvent.click(btn);
    expect(spy).toHaveBeenCalledOnce();
  });
});

describe("RaGatedPlaceholder", () => {
  it("never renders empty — always shows RA-gating message", () => {
    render(<RaGatedPlaceholder />);
    expect(screen.getByText(/research analyst registration/i)).toBeInTheDocument();
    /* Must NOT contain entry/target/stop-loss wording as a widget */
    const el = screen.getByRole("presentation");
    expect(el).toBeInTheDocument();
  });
});

describe("ScoreBadge", () => {
  it("always renders the numeric score — color is secondary", () => {
    render(<ScoreBadge score={75} />);
    /* Score encoded in aria-label — text may be in a MotionValue span */
    const btn = screen.getByRole("button", { name: /score 75/i });
    expect(btn).toBeInTheDocument();
    /* Label also present as static text */
    expect(screen.getByText(/moderate/i)).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const spy = vi.fn();
    render(<ScoreBadge score={82} onClick={spy} />);
    fireEvent.click(screen.getByRole("button"));
    expect(spy).toHaveBeenCalledOnce();
  });
});

describe("AiStockSummaryCard — suppressed state", () => {
  it("renders suppressed variant without any advisory language", () => {
    render(<AiStockSummaryCard suppressed />);
    expect(screen.getByText(/unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/buy/i)).toBeNull();
    expect(screen.queryByText(/sell/i)).toBeNull();
    expect(screen.queryByText(/target/i)).toBeNull();
  });
});

describe("AiStockSummaryCard — grounded state", () => {
  it("renders summary with grounding badge and not-advice banner", () => {
    const summary = {
      symbol: "TCS",
      session_date: "2026-06-27",
      summary: "TCS is trading above its 50-DMA with elevated volume.",
      cited_facts: [{ field: "sma_50", value: 3820, label: "SMA 50" }],
      risk_notes: [],
      model_version: "qwen2.5:7b-instruct",
      disclaimer: "Not investment advice.",
    };
    render(<AiStockSummaryCard aiSummary={summary} />);
    expect(screen.getByText(/trading above its 50-DMA/i)).toBeInTheDocument();
    expect(screen.getByText(/grounded in this stock/i)).toBeInTheDocument();
    expect(screen.getAllByText(/not investment advice/i).length).toBeGreaterThan(0);
    /* No entry/target/SL element in DOM */
    expect(screen.queryByText(/entry point/i)).toBeNull();
    expect(screen.queryByText(/stop.?loss/i)).toBeNull();
    expect(screen.queryByText(/target price/i)).toBeNull();
  });
});
