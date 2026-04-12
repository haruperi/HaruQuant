"""Live Trading Dashboard.

Real-time monitoring dashboard for multi-strategy live trading system.
Shows portfolio status, strategy statistics, and recent activity.
"""

import contextlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Try to import rich for fancy display, fall back to simple text
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class Dashboard:
    """Live trading monitoring dashboard."""

    def __init__(
        self,
        log_file: str = "backend/logs/multi_strategy/multi_strategy.log",
        state_file: str = "multi_strategy_state.json",
        refresh_interval: int = 5,
    ):
        """Initialize dashboard.

        Args:
            log_file: Path to main log file
            state_file: Path to state file
            refresh_interval: Refresh interval in seconds
        """
        self.log_file = Path(log_file)
        self.state_file = Path(state_file)
        self.refresh_interval = refresh_interval

        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        self._last_log_lines: List[str] = []
        self._portfolio_data: Dict[str, Any] = {}
        self._strategy_data: List[Dict[str, Any]] = []

    def run(self):
        """Run the dashboard."""
        if RICH_AVAILABLE:
            self._run_rich_dashboard()
        else:
            self._run_simple_dashboard()

    def _run_rich_dashboard(self):
        """Run dashboard with rich library."""
        self.console.print("[bold green]Live Trading Dashboard[/bold green]")
        self.console.print(f"Refresh interval: {self.refresh_interval}s")
        self.console.print("Press Ctrl+C to exit\n")

        try:
            with Live(
                self._generate_rich_layout(),
                refresh_per_second=1 / self.refresh_interval,
                console=self.console,
            ) as live:
                while True:
                    time.sleep(self.refresh_interval)
                    live.update(self._generate_rich_layout())

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped[/yellow]")

    def _generate_rich_layout(self) -> Layout:
        """Generate rich layout with all panels."""
        # Read state file for live data
        self._read_state_file()

        # Read recent log lines
        self._read_log_file()

        # Create layout
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=10),
        )

        # Header
        header_text = Text()
        header_text.append("Live Trading Dashboard", style="bold white on blue")
        header_text.append(
            f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="white on blue"
        )
        layout["header"].update(Panel(header_text, border_style="blue"))

        # Main section - split between portfolio and strategies
        layout["main"].split_row(
            Layout(name="portfolio", ratio=1), Layout(name="strategies", ratio=2)
        )

        # Portfolio panel
        layout["main"]["portfolio"].update(self._create_portfolio_panel())

        # Strategies panel
        layout["main"]["strategies"].update(self._create_strategies_panel())

        # Footer - recent logs
        layout["footer"].update(self._create_logs_panel())

        return layout

    def _create_portfolio_panel(self) -> Panel:
        """Create portfolio summary panel."""
        portfolio = self._portfolio_data

        if not portfolio:
            return Panel(
                "[yellow]No portfolio data available[/yellow]",
                title="Portfolio",
                border_style="cyan",
            )

        # Create table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        # Add rows
        table.add_row("Balance", f"{portfolio.get('balance', 0):.2f}")
        table.add_row("Equity", f"{portfolio.get('equity', 0):.2f}")

        profit = portfolio.get("profit", 0)
        profit_style = "green" if profit >= 0 else "red"
        table.add_row("P&L", f"[{profit_style}]{profit:+.2f}[/{profit_style}]")

        table.add_row("Margin", f"{portfolio.get('margin', 0):.2f}")
        table.add_row("Free Margin", f"{portfolio.get('free_margin', 0):.2f}")

        margin_level = portfolio.get("margin_level", 0)
        ml_style = (
            "green" if margin_level > 200 else "yellow" if margin_level > 100 else "red"
        )
        table.add_row("Margin Level", f"[{ml_style}]{margin_level:.1f}%[/{ml_style}]")

        table.add_row("", "")
        table.add_row("Total Positions", str(portfolio.get("total_positions", 0)))
        table.add_row("Buy Positions", str(portfolio.get("buy_positions", 0)))
        table.add_row("Sell Positions", str(portfolio.get("sell_positions", 0)))

        return Panel(
            table, title="[bold cyan]Portfolio[/bold cyan]", border_style="cyan"
        )

    def _create_strategies_panel(self) -> Panel:
        """Create strategies summary panel."""
        strategies = self._strategy_data

        if not strategies:
            return Panel(
                "[yellow]No strategy data available[/yellow]",
                title="Strategies",
                border_style="green",
            )

        # Create table
        table = Table(show_header=True, box=None)
        table.add_column("Strategy", style="cyan")
        table.add_column("Symbol", style="yellow")
        table.add_column("TF", style="white")
        table.add_column("Signals", style="blue", justify="right")
        table.add_column("Trades", style="green", justify="right")
        table.add_column("Failed", style="red", justify="right")
        table.add_column("Last Signal", style="white")

        # Add rows
        for strategy in strategies:
            last_signal = strategy.get("last_signal_time")
            if last_signal:
                try:
                    dt = datetime.fromisoformat(last_signal)
                    last_signal_str = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    last_signal_str = "-"
            else:
                last_signal_str = "-"

            table.add_row(
                strategy.get("name", "Unknown"),
                strategy.get("symbol", ""),
                strategy.get("timeframe", ""),
                str(strategy.get("signals_detected", 0)),
                str(strategy.get("trades_executed", 0)),
                str(strategy.get("trades_failed", 0)),
                last_signal_str,
            )

        return Panel(
            table, title="[bold green]Strategies[/bold green]", border_style="green"
        )

    def _create_logs_panel(self) -> Panel:
        """Create recent logs panel."""
        if not self._last_log_lines:
            return Panel(
                "[yellow]No recent logs[/yellow]",
                title="Recent Logs",
                border_style="white",
            )

        log_text = Text()
        for line in self._last_log_lines[-8:]:  # Show last 8 lines
            # Color code based on log level
            if "ERROR" in line:
                log_text.append(line + "\n", style="red")
            elif "WARNING" in line:
                log_text.append(line + "\n", style="yellow")
            elif "SIGNAL" in line or "TRADE" in line:
                log_text.append(line + "\n", style="green bold")
            else:
                log_text.append(line + "\n", style="white")

        return Panel(
            log_text, title="[bold white]Recent Logs[/bold white]", border_style="white"
        )

    def _print_simple_dashboard_header(self):
        """Print simple dashboard header."""
        # Clear screen
        os.system("cls" if os.name == "nt" else "clear")

        # Print header
        print("=" * 80)
        print(
            f"Live Trading Dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("=" * 80)

    def _print_portfolio_summary(self):
        """Print portfolio summary in simple mode."""
        print("\nPORTFOLIO:")
        print("-" * 40)
        portfolio = self._portfolio_data
        if portfolio:
            print(f"Balance:       {portfolio.get('balance', 0):.2f}")
            print(f"Equity:        {portfolio.get('equity', 0):.2f}")
            print(f"P&L:           {portfolio.get('profit', 0):+.2f}")
            print(f"Margin:        {portfolio.get('margin', 0):.2f}")
            print(f"Free Margin:   {portfolio.get('free_margin', 0):.2f}")
            print(f"Margin Level:  {portfolio.get('margin_level', 0):.1f}%")
            print(f"Total Positions: {portfolio.get('total_positions', 0)}")
        else:
            print("No portfolio data available")

    def _print_strategies_summary(self):
        """Print strategies summary in simple mode."""
        print("\nSTRATEGIES:")
        print("-" * 80)
        print(
            f"{'Strategy':<20} {'Symbol':<10} {'TF':<5} {'Signals':<8} "
            f"{'Trades':<8} {'Failed':<8} {'Last Signal'}"
        )
        print("-" * 80)

        strategies = self._strategy_data
        if strategies:
            for strategy in strategies:
                last_signal = strategy.get("last_signal_time", "-")
                if last_signal and last_signal != "-":
                    try:
                        dt = datetime.fromisoformat(last_signal)
                        last_signal = dt.strftime("%H:%M:%S")
                    except (ValueError, TypeError):
                        pass

                print(
                    f"{strategy.get('name', ''):<20} "
                    f"{strategy.get('symbol', ''):<10} "
                    f"{strategy.get('timeframe', ''):<5} "
                    f"{strategy.get('signals_detected', 0):<8} "
                    f"{strategy.get('trades_executed', 0):<8} "
                    f"{strategy.get('trades_failed', 0):<8} "
                    f"{last_signal}"
                )
        else:
            print("No strategy data available")

    def _print_recent_logs(self):
        """Print recent logs in simple mode."""
        print("\nRECENT LOGS:")
        print("-" * 80)
        if self._last_log_lines:
            for line in self._last_log_lines[-5:]:
                print(line)
        else:
            print("No recent logs")

        print("\n" + "=" * 80)

    def _run_simple_dashboard(self):
        """Run simple text-based dashboard."""
        print("Live Trading Dashboard (Simple Mode)")
        print(f"Refresh interval: {self.refresh_interval}s")
        print("Press Ctrl+C to exit\n")
        print("Note: Install 'rich' for better display: pip install rich\n")

        try:
            while True:
                # Read data
                self._read_state_file()
                self._read_log_file()

                # Print sections
                self._print_simple_dashboard_header()
                self._print_portfolio_summary()
                self._print_strategies_summary()
                self._print_recent_logs()

                # Sleep
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\nDashboard stopped")

    def _read_state_file(self):
        """Read state file for current data."""
        # For now, we'll simulate with dummy data
        # In production, the multi_engine should write status to a JSON file
        # that the dashboard can read

        # Try to read from a status file if it exists
        status_file = Path("multi_strategy_status.json")
        if status_file.exists():
            with contextlib.suppress(Exception), open(status_file, "r") as f:
                data = json.load(f)
                self._portfolio_data = data.get("portfolio", {})
                self._strategy_data = data.get("strategies", [])
        else:
            # Dummy data for testing
            self._portfolio_data = {
                "balance": 10000.00,
                "equity": 10050.00,
                "profit": 50.00,
                "margin": 200.00,
                "free_margin": 9800.00,
                "margin_level": 5025.0,
                "total_positions": 3,
                "buy_positions": 2,
                "sell_positions": 1,
            }

            self._strategy_data = [
                {
                    "name": "XAUUSD_Trend",
                    "symbol": "XAUUSD",
                    "timeframe": "M1",
                    "signals_detected": 5,
                    "trades_executed": 4,
                    "trades_failed": 1,
                    "last_signal_time": datetime.now().isoformat(),
                },
                {
                    "name": "EURUSD_Trend",
                    "symbol": "EURUSD",
                    "timeframe": "M1",
                    "signals_detected": 3,
                    "trades_executed": 3,
                    "trades_failed": 0,
                    "last_signal_time": None,
                },
            ]

    def _read_log_file(self):
        """Read recent lines from log file."""
        if not self.log_file.exists():
            return

        with (
            contextlib.suppress(Exception),
            open(self.log_file, "r", encoding="utf-8") as f,
        ):
            # Read last 20 lines
            lines = f.readlines()
            self._last_log_lines = [
                line.strip() for line in lines[-20:] if line.strip()
            ]


def main():
    """Run dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Trading Dashboard")
    parser.add_argument(
        "--log",
        default="backend/logs/multi_strategy/multi_strategy.log",
        help="Path to log file",
    )
    parser.add_argument(
        "--state", default="multi_strategy_state.json", help="Path to state file"
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Refresh interval in seconds"
    )

    args = parser.parse_args()

    dashboard = Dashboard(
        log_file=args.log, state_file=args.state, refresh_interval=args.interval
    )

    dashboard.run()


if __name__ == "__main__":
    main()
