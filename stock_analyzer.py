"""
Stock Market Analyzer — Like /crypto but for stocks.
yfinance + LLM signals for portfolio management.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger("StockAnalyzer")


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class StockAnalyzer:
    """
    Stock market analyzer with live quotes, technical signals, and LLM narratives.
    Uses yfinance for data. Falls back to mock data if not installed.
    """

    MOCK_STOCKS = {
        "AAPL": {"name": "Apple Inc.", "price": 189.30, "prev_close": 187.15, "sector": "Technology"},
        "TSLA": {"name": "Tesla Inc.", "price": 251.12, "prev_close": 265.40, "sector": "Automotive"},
        "MSFT": {"name": "Microsoft Corp.", "price": 415.25, "prev_close": 412.80, "sector": "Technology"},
        "GOOGL": {"name": "Alphabet Inc.", "price": 172.63, "prev_close": 170.90, "sector": "Technology"},
        "AMZN": {"name": "Amazon.com Inc.", "price": 195.18, "prev_close": 193.45, "sector": "E-Commerce"},
        "NVDA": {"name": "NVIDIA Corp.", "price": 876.34, "prev_close": 850.20, "sector": "Semiconductors"},
        "META": {"name": "Meta Platforms Inc.", "price": 502.07, "prev_close": 498.30, "sector": "Technology"},
        "AMD": {"name": "Advanced Micro Devices", "price": 178.22, "prev_close": 181.54, "sector": "Semiconductors"},
        "NFLX": {"name": "Netflix Inc.", "price": 628.90, "prev_close": 621.70, "sector": "Media"},
        "SPY": {"name": "S&P 500 ETF", "price": 507.22, "prev_close": 505.10, "sector": "ETF"},
    }

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._yf_available = self._check_yfinance()
        self.watchlist: List[str] = ["AAPL", "TSLA", "NVDA", "MSFT"]
        self.portfolio: Dict[str, Dict] = {}  # {symbol: {shares, avg_cost}}
        self._load_state()

    def _check_yfinance(self) -> bool:
        try:
            import yfinance
            return True
        except ImportError:
            logger.info("yfinance not installed. Using mock data. Run: pip install yfinance")
            return False

    def _load_state(self):
        path = "stock_portfolio.json"
        try:
            if os.path.exists(path):
                with open(path) as f:
                    state = json.load(f)
                    self.watchlist = state.get("watchlist", self.watchlist)
                    self.portfolio = state.get("portfolio", {})
        except Exception:
            pass

    def _save_state(self):
        try:
            with open("stock_portfolio.json", "w") as f:
                json.dump({"watchlist": self.watchlist, "portfolio": self.portfolio}, f, indent=2)
        except Exception:
            pass

    def _get_yfinance_data(self, symbol: str) -> Optional[Dict]:
        """Fetch real data from yfinance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            hist = ticker.history(period="5d")
            if hist.empty:
                return None

            closes = hist["Close"].tolist()
            price = closes[-1]
            prev_close = closes[-2] if len(closes) >= 2 else price

            # Simple RSI (14)
            changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [c for c in changes if c > 0]
            losses = [-c for c in changes if c < 0]
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 1
            rs = avg_gain / avg_loss if avg_loss else 0
            rsi = 100 - (100 / (1 + rs)) if avg_loss else 50

            return {
                "symbol": symbol.upper(),
                "name": info.get("longName", symbol),
                "price": round(price, 2),
                "prev_close": round(prev_close, 2),
                "change": round(price - prev_close, 2),
                "change_pct": round((price - prev_close) / prev_close * 100, 2),
                "rsi": round(rsi, 1),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "sector": info.get("sector", "Unknown"),
                "source": "yfinance"
            }
        except Exception as e:
            logger.warning(f"yfinance error for {symbol}: {e}")
            return None

    def _get_mock_data(self, symbol: str) -> Dict:
        """Return mock stock data with slight randomization."""
        import random
        sym = symbol.upper()
        if sym in self.MOCK_STOCKS:
            base = self.MOCK_STOCKS[sym].copy()
        else:
            base = {"name": f"{sym} Corporation", "price": 100.0, "prev_close": 98.5, "sector": "Unknown"}

        noise = random.uniform(-0.02, 0.02)
        price = round(base["price"] * (1 + noise), 2)
        prev = base["prev_close"]
        change = round(price - prev, 2)
        rsi = round(random.uniform(30, 70), 1)

        return {
            "symbol": sym,
            "name": base["name"],
            "price": price,
            "prev_close": prev,
            "change": change,
            "change_pct": round(change / prev * 100, 2),
            "rsi": rsi,
            "volume": random.randint(1_000_000, 50_000_000),
            "market_cap": random.randint(100_000_000, 3_000_000_000_000),
            "pe_ratio": round(random.uniform(10, 45), 1),
            "sector": base.get("sector", "Unknown"),
            "source": "simulation"
        }

    def get_quote(self, symbol: str) -> Dict:
        """Get a real-time (or simulated) stock quote."""
        if self._yf_available:
            data = self._get_yfinance_data(symbol)
            if data:
                return data
        return self._get_mock_data(symbol)

    def get_signal(self, symbol: str) -> Dict:
        """Get a buy/sell/hold signal with LLM narrative."""
        data = self.get_quote(symbol)
        rsi = data.get("rsi", 50)
        change_pct = data.get("change_pct", 0)

        # Simple Rule-based signal
        if rsi < 35 and change_pct < -1.5:
            raw_signal = "BUY"
            confidence = "High"
        elif rsi > 65 and change_pct > 1.5:
            raw_signal = "SELL"
            confidence = "High"
        elif rsi < 45 and change_pct < 0:
            raw_signal = "BUY"
            confidence = "Medium"
        elif rsi > 55 and change_pct > 0:
            raw_signal = "SELL"
            confidence = "Medium"
        else:
            raw_signal = "HOLD"
            confidence = "Medium"

        # LLM narrative
        narrative = ""
        if self.llm:
            try:
                prompt = (
                    f"You are a financial analyst. Analyze this stock and give a brief 2-3 sentence insight.\n\n"
                    f"Stock: {data['name']} ({data['symbol']})\n"
                    f"Price: ${data['price']:,.2f} | Change: {data['change_pct']:+.2f}%\n"
                    f"RSI: {rsi} | P/E: {data.get('pe_ratio', 'N/A')} | Sector: {data.get('sector', 'N/A')}\n"
                    f"Technical Signal: {raw_signal} ({confidence} confidence)\n\n"
                    f"Give actionable trading insight. Be direct and professional."
                )
                narrative = self.llm.call(prompt, max_tokens=150)
            except Exception as e:
                narrative = f"Signal: {raw_signal} based on RSI={rsi:.0f} and price action."

        return {
            "symbol": data["symbol"],
            "name": data["name"],
            "price": data["price"],
            "change_pct": data["change_pct"],
            "rsi": rsi,
            "signal": raw_signal,
            "confidence": confidence,
            "narrative": narrative,
            "source": data.get("source", "unknown")
        }

    def portfolio_report(self, symbols: Optional[List[str]] = None) -> Dict:
        """Generate a portfolio overview for a list of symbols."""
        symbols = symbols or self.watchlist
        report = {"holdings": [], "total_value": 0.0, "gainers": [], "losers": []}

        for sym in symbols:
            q = self.get_quote(sym)
            held = self.portfolio.get(sym.upper(), {})
            shares = held.get("shares", 0)
            avg_cost = held.get("avg_cost", q["price"])
            value = q["price"] * shares if shares else 0
            pnl = (q["price"] - avg_cost) * shares if shares else 0

            entry = {
                "symbol": q["symbol"],
                "price": q["price"],
                "change_pct": q["change_pct"],
                "shares": shares,
                "value": round(value, 2),
                "pnl": round(pnl, 2),
                "rsi": q["rsi"]
            }
            report["holdings"].append(entry)
            report["total_value"] += value

            if q["change_pct"] > 0:
                report["gainers"].append(q["symbol"])
            elif q["change_pct"] < 0:
                report["losers"].append(q["symbol"])

        report["total_value"] = round(report["total_value"], 2)
        return report

    def add_to_watchlist(self, symbol: str):
        sym = symbol.upper()
        if sym not in self.watchlist:
            self.watchlist.append(sym)
            self._save_state()

    def add_to_portfolio(self, symbol: str, shares: float, avg_cost: float):
        sym = symbol.upper()
        self.portfolio[sym] = {"shares": shares, "avg_cost": avg_cost}
        if sym not in self.watchlist:
            self.watchlist.append(sym)
        self._save_state()

    def get_status(self) -> Dict:
        return {
            "yfinance_available": self._yf_available,
            "watchlist": self.watchlist,
            "portfolio_size": len(self.portfolio),
            "data_source": "yfinance (live)" if self._yf_available else "simulation (no yfinance)"
        }
