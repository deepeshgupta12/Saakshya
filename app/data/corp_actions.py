"""Ingest corporate actions from a DataSource into the corporate_actions master.

Computes the single-event backward price-adjustment factor for each action and
persists it via the repository. Cumulative factors across events are computed by
the adjuster (corp_action_adjuster.py), not here.

Price-adjustment conventions (SPEC §6.1, docs/11 §3.4):
  split  — ratio_from=1, ratio_to=new/old (e.g. 1:2 split → ratio_to=2)
            event_factor = ratio_from / ratio_to  = 1/2 = 0.5
  bonus  — ratio_from=bonus shares, ratio_to=held shares (e.g. 1:1 bonus)
            event_factor = ratio_to / (ratio_from + ratio_to)  = 1/2 = 0.5
  dividend — factor deferred (requires ex-date close; M3 enhancement)
"""

from __future__ import annotations

from app.data.base import CorpActionRow
from app.storage.repository import CorpActionRecord, Repository


def compute_event_factor(row: CorpActionRow) -> float | None:
    """Return the single-event backward price-adjustment factor, or None if not computable.

    A factor < 1 means historical prices must be multiplied down (e.g. after a split).
    Dividends require the ex-date close price for an exact factor; deferred to M3.
    """
    if row.action_type == "split" and row.ratio_from and row.ratio_to and row.ratio_to > 0:
        return row.ratio_from / row.ratio_to
    if (
        row.action_type == "bonus"
        and row.ratio_from
        and row.ratio_to
        and (row.ratio_from + row.ratio_to) > 0
    ):
        return row.ratio_to / (row.ratio_from + row.ratio_to)
    return None


def ingest_corp_actions(
    repo: Repository,
    ticker_to_stock_id: dict[str, int],
    rows: list[CorpActionRow],
    as_of_version: int = 1,
) -> int:
    """Upsert CorpActionRow list into the corporate_actions master.

    Returns the count of rows processed (unmapped tickers are skipped without error;
    duplicates on (stock_id, action_type, ex_date) are silently skipped — idempotent).
    """
    count = 0
    for row in rows:
        sid = ticker_to_stock_id.get(row.symbol)
        if sid is None:
            continue
        record = CorpActionRecord(
            stock_id=sid,
            action_type=row.action_type,
            ex_date=row.ex_date,
            ratio_from=row.ratio_from,
            ratio_to=row.ratio_to,
            dividend_amount=row.dividend_amount,
            new_symbol=row.new_symbol,
            factor=compute_event_factor(row),
            source=row.source,
            as_of_version=as_of_version,
        )
        repo.upsert_corporate_action(record)
        count += 1
    return count
