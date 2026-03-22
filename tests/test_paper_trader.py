# tests/test_paper_trader.py
from polymatt.paper_trader.portfolio import Portfolio


def test_portfolio_starts_at_bankroll():
    p = Portfolio(starting_bankroll=1000.0)
    assert p.current_bankroll == 1000.0
    assert p.total_pnl == 0.0


def test_portfolio_records_win():
    p = Portfolio(starting_bankroll=1000.0)
    p.record_closed_trade(pnl=10.0)
    assert p.wins == 1
    assert p.losses == 0
    assert p.total_pnl == 10.0


def test_portfolio_records_loss():
    p = Portfolio(starting_bankroll=1000.0)
    p.record_closed_trade(pnl=-5.0)
    assert p.losses == 1
    assert p.max_drawdown == 5.0


def test_win_rate_calculation():
    p = Portfolio(starting_bankroll=1000.0)
    p.record_closed_trade(pnl=10.0)
    p.record_closed_trade(pnl=10.0)
    p.record_closed_trade(pnl=-5.0)
    assert abs(p.win_rate() - 66.67) < 0.1


def test_breakeven_trade_not_counted_as_loss():
    p = Portfolio(starting_bankroll=1000.0)
    p.record_closed_trade(pnl=0.0)
    assert p.wins == 0
    assert p.losses == 0
    assert p.total_pnl == 0.0


from polymatt.paper_trader.trader import PaperTrader

def test_session_summary_has_required_fields():
    trader = PaperTrader(condition_id="test-id", learner=None)
    summary = trader.close_session()
    for field in ["wins", "losses", "win_rate_pct", "total_pnl", "max_drawdown"]:
        assert field in summary, f"Missing field: {field}"
