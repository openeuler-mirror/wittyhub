from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from cli.client import APIClient

app = typer.Typer(
    name="skillhub",
    help="SkillHub CLI - Agent and Skill Discovery Platform",
    add_completion=False,
)

console = Console()


@app.command()
def list(
    skip: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    category: str | None = None,
    platform: str | None = None,
    base_url: str | None = None,
):
    """List all available skills."""
    client = APIClient(base_url=base_url)

    try:
        result = client.list_skills(skip=skip, limit=limit, category=category, platform=platform)

        table = Table(title=f"Skills (Total: {result['total']})")
        table.add_column("Skill ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Category", style="magenta")
        table.add_column("Platform", style="yellow")
        table.add_column("Downloads", style="blue")

        for skill in result["skills"]:
            table.add_row(
                skill["skill_id"],
                skill["name"],
                skill.get("category", "-") or "-",
                skill.get("platform", "-") or "-",
                str(skill.get("download_count", 0)),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command()
def search(
    query: str,
    skip: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    base_url: str | None = None,
):
    """Search for skills."""
    client = APIClient(base_url=base_url)

    try:
        result = client.search_skills(query=query, skip=skip, limit=limit)

        console.print(f"\n[bold]Search Results for:[/bold] '{query}'")
        console.print(f"Found [cyan]{result['total']}[/cyan] results")
        console.print(f"Processing time: {result.get('processing_time_ms', 0)}ms\n")

        table = Table()
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Category", style="magenta")

        for hit in result["results"][:limit]:
            desc = (hit.get("description") or "-")[:50]
            table.add_row(
                hit.get("name", "-"),
                f"{desc}..." if len(desc) == 50 else desc,
                hit.get("category", "-") or "-",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command()
def get(
    skill_id: str,
    base_url: str | None = None,
):
    """Get details of a specific skill."""
    client = APIClient(base_url=base_url)

    try:
        skill = client.get_skill(skill_id)

        console.print(f"\n[bold cyan]{skill['name']}[/bold cyan] (v{skill.get('version', 'N/A')})")
        console.print(f"[dim]ID:[/dim] {skill['skill_id']}")
        console.print(f"[dim]Author:[/dim] {skill.get('author', 'Unknown')}")
        console.print(f"[dim]Source:[/dim] {skill['source']}")
        console.print(f"[dim]Category:[/dim] {skill.get('category', '-') or '-'}")
        console.print(f"[dim]Platform:[/dim] {skill.get('platform', '-') or '-'}")
        console.print(f"[dim]Downloads:[/dim] {skill.get('download_count', 0)}")

        if skill.get("description"):
            console.print(f"\n[bold]Description:[/bold]\n{skill['description']}")

        if skill.get("tags"):
            console.print(f"\n[bold]Tags:[/bold] {', '.join(skill['tags'])}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command()
def download(
    skill_id: str,
    base_url: str | None = None,
):
    """Download a skill."""
    client = APIClient(base_url=base_url)

    try:
        result = client.download_skill(skill_id)
        console.print(f"[green]Download URL:[/green] {result['download_url']}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command()
def audit(
    skill_id: str,
    base_url: str | None = None,
):
    """Get security audit for a skill."""
    client = APIClient(base_url=base_url)

    try:
        result = client.audit_skill(skill_id)

        if "error" in result:
            console.print(f"[yellow]No audit found for {skill_id}[/yellow]")
            return

        console.print(f"\n[bold]Security Audit for {skill_id}[/bold]")
        console.print(f"[dim]Risk Level:[/dim] ", end="")
        risk_level = result.get("risk_level", "unknown")
        color = {"critical": "red", "high": "red", "medium": "yellow", "low": "green", "unknown": "dim"}.get(risk_level, "white")
        console.print(f"[{color}]{risk_level.upper()}[/{color}]")

        if signals := result.get("risk_signals"):
            console.print(f"\n[bold]Risk Signals:[/bold]")
            for signal in signals:
                severity = signal.get("severity", "unknown")
                console.print(f"  - [{severity.upper()}] {signal.get('name', 'Unknown')}: {signal.get('description', '')}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


@app.command()
def reindex(
    base_url: str | None = None,
):
    """Trigger a full reindex of all skills."""
    client = APIClient(base_url=base_url)

    try:
        result = client.reindex()
        console.print(f"[green]Reindex completed![/green]")
        console.print(f"Indexed: {result.get('indexed_count', 0)} / {result.get('total_skills', 0)}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    app()