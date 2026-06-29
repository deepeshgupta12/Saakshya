"""Golden tests for the corporate-action back-adjuster (SPEC §6.1, docs/steps/01).

Critical-logic tests (docs/27 §0.1): every test uses a hand-verified golden value.
No network calls; no I/O. Pure function tests only.

Conventions:
  ratio_from / ratio_to for splits  : old_shares / new_shares (e.g. 1:2 split → 1/2)
  ratio_from / ratio_to for bonuses : bonus_shares / held_shares (e.g. 1:1 bonus → 1/1)
  event_factor for both             : pre-event price is multiplied down to align with
                                      the post-event price scale.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.data.base import CorpActionRow
from app.data.corp_action_adjuster import compute_adj_factors
from app.data.corp_actions import compute_event_factor
from app.storage.repository import CorpActionRecord

# ---------------------------------------------------------------------------
# compute_event_factor (per-event)
# ---------------------------------------------------------------------------

def _ca_record(action_type: str, ratio_from: float, ratio_to: float) -> CorpActionRecord:
    return CorpActionRecord(
        stock_id=1,
        action_type=action_type,
        ex_date=date(2024, 1, 15),
        ratio_from=ratio_from,
        ratio_to=ratio_to,
        factor=None,
        source="test",
    )


def _ca_row(action_type: str, ratio_from: float, ratio_to: float) -> CorpActionRow:
    return CorpActionRow(
        symbol="TEST",
        action_type=action_type,
        ex_date=date(2024, 1, 15),
        ratio_from=ratio_from,
        ratio_to=ratio_to,
        source="test",
    )


def test_split_1_2_event_factor() -> None:
    """1:2 split → price halves → event_factor = 0.5."""
    row = _ca_row("split", ratio_from=1.0, ratio_to=2.0)
    assert compute_event_factor(row) == pytest.approx(0.5)


def test_split_1_5_event_factor() -> None:
    """1:5 split → price becomes 1/5 → event_factor = 0.2."""
    row = _ca_row("split", ratio_from=1.0, ratio_to=5.0)
    assert compute_event_factor(row) == pytest.approx(0.2)


def test_bonus_1_1_event_factor() -> None:
    """1:1 bonus (1 extra per 1 held → total 2) → price halves → event_factor = 0.5."""
    row = _ca_row("bonus", ratio_from=1.0, ratio_to=1.0)
    assert compute_event_factor(row) == pytest.approx(0.5)


def test_bonus_2_3_event_factor() -> None:
    """2:3 bonus (2 extra per 3 held → total 5) → factor = 3/5 = 0.6."""
    row = _ca_row("bonus", ratio_from=2.0, ratio_to=3.0)
    assert compute_event_factor(row) == pytest.approx(0.6)


def test_dividend_event_factor_is_none() -> None:
    """Dividends have no computable price factor without the ex-date close (deferred)."""
    row = CorpActionRow(
        symbol="TEST", action_type="dividend", ex_date=date(2024, 1, 15),
        dividend_amount=5.0, source="test"
    )
    assert compute_event_factor(row) is None


# ---------------------------------------------------------------------------
# compute_adj_factors (cumulative, per-date)
# ---------------------------------------------------------------------------

def _split_record(ex_date: date, factor: float) -> CorpActionRecord:
    return CorpActionRecord(
        stock_id=1, action_type="split",
        ex_date=ex_date, ratio_from=1.0, ratio_to=1.0 / factor,
        factor=factor, source="test",
    )


def test_no_actions_all_ones() -> None:
    """No corp actions → every date gets adj_factor = 1.0."""
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    factors = compute_adj_factors([], dates)
    assert factors == [pytest.approx(1.0)] * 3


def test_empty_dates_returns_empty() -> None:
    action = _split_record(date(2024, 1, 15), 0.5)
    assert compute_adj_factors([action], []) == []


def test_split_1_2_backward_adjustment() -> None:
    """1:2 split (factor=0.5) on 2024-01-15.

    Bars BEFORE the ex_date should be multiplied by 0.5 (price was double pre-split).
    Bars ON or AFTER the ex_date need no further adjustment.
    """
    action = _split_record(date(2024, 1, 15), factor=0.5)
    dates = [date(2024, 1, 14), date(2024, 1, 15), date(2024, 1, 16)]
    factors = compute_adj_factors([action], dates)

    assert factors[0] == pytest.approx(0.5)   # before split → adjust down
    assert factors[1] == pytest.approx(1.0)   # on ex_date → no adjustment
    assert factors[2] == pytest.approx(1.0)   # after → no adjustment


def test_bonus_1_1_backward_adjustment() -> None:
    """1:1 bonus (factor=0.5) on 2024-06-10 — same halving effect."""
    action = CorpActionRecord(
        stock_id=1, action_type="bonus", ex_date=date(2024, 6, 10),
        ratio_from=1.0, ratio_to=1.0, factor=0.5, source="test",
    )
    dates = [date(2024, 6, 9), date(2024, 6, 10), date(2024, 6, 11)]
    factors = compute_adj_factors([action], dates)

    assert factors[0] == pytest.approx(0.5)
    assert factors[1] == pytest.approx(1.0)
    assert factors[2] == pytest.approx(1.0)


def test_two_events_cumulative_factor() -> None:
    """Split (2020-01-15) + bonus (2022-06-10) — cumulative factor is the product.

    Before both events  → 0.5 × 0.5 = 0.25
    On split ex_date    → 0.5   (only bonus adjustment applies going forward)
    Between events      → 0.5
    On bonus ex_date    → 1.0   (no further adjustments)
    """
    actions = [
        _split_record(date(2020, 1, 15), factor=0.5),
        CorpActionRecord(
            stock_id=1, action_type="bonus", ex_date=date(2022, 6, 10),
            ratio_from=1.0, ratio_to=1.0, factor=0.5, source="test",
        ),
    ]
    dates = [
        date(2019, 1, 1),    # 0 → before both
        date(2020, 1, 15),   # 1 → on first event
        date(2022, 6, 9),    # 2 → between events
        date(2022, 6, 10),   # 3 → on second event
        date(2024, 1, 1),    # 4 → after both
    ]
    factors = compute_adj_factors(actions, dates)

    assert factors[0] == pytest.approx(0.25)
    assert factors[1] == pytest.approx(0.5)
    assert factors[2] == pytest.approx(0.5)
    assert factors[3] == pytest.approx(1.0)
    assert factors[4] == pytest.approx(1.0)


def test_adjusted_series_is_continuous_around_split() -> None:
    """After adjustment, adj_close should be continuous across the split boundary.

    Pre-split: raw_close = 1000.0  → adj = 1000 × 0.5 = 500
    Post-split: raw_close = 500.0  → adj = 500  × 1.0 = 500  ← no artificial gap
    """
    action = _split_record(date(2024, 1, 15), factor=0.5)
    pre_date = date(2024, 1, 14)
    post_date = date(2024, 1, 15)

    factors = compute_adj_factors([action], [pre_date, post_date])
    raw_closes = [1000.0, 500.0]
    adj_closes = [r * f for r, f in zip(raw_closes, factors, strict=True)]

    assert adj_closes[0] == pytest.approx(500.0)
    assert adj_closes[1] == pytest.approx(500.0)
    # Raw values are unchanged — the adj computation is non-mutating.
    assert raw_closes[0] == 1000.0
    assert raw_closes[1] == 500.0


def test_action_with_no_factor_is_ignored() -> None:
    """Corp actions whose factor is None (e.g. dividends) do not alter other dates."""
    action_no_factor = CorpActionRecord(
        stock_id=1, action_type="dividend", ex_date=date(2024, 1, 15),
        factor=None, source="test",
    )
    action_split = _split_record(date(2024, 3, 1), factor=0.5)
    dates = [date(2024, 1, 14), date(2024, 3, 1)]
    factors = compute_adj_factors([action_no_factor, action_split], dates)

    assert factors[0] == pytest.approx(0.5)   # split at 2024-03-01 still applies
    assert factors[1] == pytest.approx(1.0)
