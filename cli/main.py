from pathlib import Path
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
    """Download a skill (get download URL only)."""
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
def install(
    skill_id: str,
    base_url: str | None = None,
    target_dir: str | None = None,
):
    """Install a skill to ~/.agents/skills/ directory."""
    import urllib.request
    import zipfile
    import io
    import os
    import shutil

    client = APIClient(base_url=base_url)

    try:
        result = client.download_skill(skill_id)
        download_url = result["download_url"]

        skill = client.get_skill(skill_id)
        skill_name = skill_id.split(":")[0].split("/")[-1]
        version = skill.get("version", "main")

        target = Path(target_dir) if target_dir else Path.home() / ".agents" / "skills"
        target_skill_dir = target / skill_name

        console.print(f"[cyan]Installing {skill_name} to {target_skill_dir}...[/cyan]")

        target.mkdir(parents=True, exist_ok=True)

        if target_skill_dir.exists():
            shutil.rmtree(target_skill_dir)

        console.print(f"[dim]Downloading from {download_url}...[/dim]")
        try:
            response = urllib.request.urlopen(download_url, timeout=30)
            zip_data = io.BytesIO(response.read())

            with zipfile.ZipFile(zip_data, 'r') as zip_ref:
                repo_root = None
                for name in zip_ref.namelist():
                    if "/" in name and not name.startswith("."):
                        repo_root = name.split("/")[0]
                        break

                skills_prefix = f"{repo_root}/skills/" if repo_root else "skills/"
                skill_prefix = None
                skill_files = []

                for name in zip_ref.namelist():
                    if not name.startswith(skills_prefix):
                        continue
                    relative = name[len(skills_prefix):]
                    parts = relative.split("/")
                    if len(parts) >= 2 and parts[0] and parts[1]:
                        skill_subfolder = parts[1]
                        if skill_subfolder == skill_name or skill_subfolder == skill_name.replace("/", "-"):
                            skill_prefix = f"{skills_prefix}{parts[0]}/{parts[1]}/"
                            break

                if not skill_prefix:
                    for name in zip_ref.namelist():
                        if not name.startswith(skills_prefix):
                            continue
                        relative = name[len(skills_prefix):]
                        parts = relative.split("/")
                        if len(parts) >= 2 and parts[0] and parts[1]:
                            skill_subfolder = parts[1]
                            if skill_subfolder.replace("-", "").replace("_", "").lower().startswith(skill_name.replace("-", "").replace("_", "").lower()[:10]):
                                skill_prefix = f"{skills_prefix}{parts[0]}/{parts[1]}/"
                                break

                if not skill_prefix:
                    console.print(f"[yellow]No skill folder found for '{skill_name}' in archive[/yellow]")
                    console.print(f"[dim]Available skills folders in archive:[/dim]")
                    seen_folders = set()
                    for name in zip_ref.namelist():
                        if name.startswith(skills_prefix):
                            parts = name[len(skills_prefix):].split("/")
                            if len(parts) > 1:
                                seen_folders.add(f"{parts[0]}/{parts[1]}")
                    for folder in sorted(seen_folders)[:20]:
                        console.print(f"  - {folder}")
                    return

                for name in zip_ref.namelist():
                    if name.startswith(skill_prefix):
                        skill_files.append(name)

                if not skill_files:
                    console.print(f"[yellow]No files found for skill prefix '{skill_prefix}'[/yellow]")
                    return

                target_skill_dir.mkdir(parents=True, exist_ok=True)
                for name in skill_files:
                    relative_path = name[len(skill_prefix):]
                    if relative_path:
                        target_path = target_skill_dir / relative_path
                        if name.endswith("/"):
                            target_path.mkdir(parents=True, exist_ok=True)
                        else:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            with zip_ref.open(name) as source:
                                with open(target_path, 'wb') as target_file:
                                    target_file.write(source.read())

            if target_skill_dir.exists() and any(target_skill_dir.iterdir()):
                console.print(f"[green]Successfully installed {skill_name}![/green]")
                console.print(f"[dim]Location: {target_skill_dir}[/dim]")
            else:
                console.print(f"[yellow]Warning: Skill folder is empty[/yellow]")

        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            console.print(f"[yellow]Try downloading manually:[/yellow] {download_url}")

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