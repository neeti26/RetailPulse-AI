"""
RetailPulse AI — CLI Entry Point
Run with: python -m retailpulse
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.text import Text

console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🏬  RetailPulse AI — Mall Intelligence Agent        ║
║          Powered by Google ADK + Gemini + MongoDB            ║
╚══════════════════════════════════════════════════════════════╝
"""

EXAMPLE_QUERIES = [
    "Which tenants had the highest revenue this week?",
    "Show me footfall trends for Zone-C over the last 7 days",
    "Run the daily anomaly scan and log any issues",
    "Find underperforming tenants and create a promotion plan",
    "Generate a weekly summary report",
    "Which tenants have leases expiring in the next 60 days?",
    "What were the peak footfall hours yesterday?",
    "Compare this month's revenue to last month",
]


def print_banner():
    console.print(BANNER, style="bold cyan")
    console.print(
        Panel(
            "\n".join(f"  • {q}" for q in EXAMPLE_QUERIES[:4]),
            title="[bold]Example queries[/bold]",
            border_style="dim",
        )
    )
    console.print(
        "\nType [bold cyan]'help'[/bold cyan] for more examples, "
        "[bold cyan]'quit'[/bold cyan] to exit.\n"
    )


async def run_cli():
    """Run the RetailPulse AI agent in interactive CLI mode."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    from retailpulse.agent import root_agent

    print_banner()

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="retailpulse_cli",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="retailpulse_cli",
        user_id="mall_manager",
    )

    console.print(
        f"[dim]Session started. Connected to: "
        f"{os.getenv('MONGODB_URI', 'mongodb://localhost:27017/retailpulse')}[/dim]\n"
    )

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input.strip():
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "help":
            console.print(
                Panel(
                    "\n".join(f"  • {q}" for q in EXAMPLE_QUERIES),
                    title="[bold]Example queries[/bold]",
                    border_style="cyan",
                )
            )
            continue

        console.print("\n[bold blue]RetailPulse AI[/bold blue]", end=" ")
        console.print("[dim]thinking...[/dim]")

        try:
            content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_input)],
            )

            full_response = ""
            async for event in runner.run_async(
                user_id="mall_manager",
                session_id=session.id,
                new_message=content,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                full_response += part.text

            if full_response:
                console.print(
                    Panel(
                        Markdown(full_response),
                        title="[bold blue]RetailPulse AI[/bold blue]",
                        border_style="blue",
                    )
                )
            else:
                console.print("[dim]No response received.[/dim]")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            if os.getenv("DEBUG", "false").lower() == "true":
                import traceback
                traceback.print_exc()

        console.print()


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
