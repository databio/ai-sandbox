#!/usr/bin/env python3
"""Workspace management CLI

A workspace is a directory containing a workspace.toml file that
specifies a set of git repositories to manage together. It is designed to
be a folder you open in vscode, with a bunch of related git repos under a
'repos/' subdirectory. In this folder, you use CLI AI tools to work on 
projects spanning those repos. The context, prompts, journals, notes, plans, 
etc. for the workspace are stored in the workspace folder itself, outside the
specific repos.

Usage:
    ./workspace.py setup <name>              Setup a workspace (clone repos, create symlinks)
    ./workspace.py gitcheck [name]           Check for uncommitted/unpushed git changes
    ./workspace.py link                      Link Obsidian notes to workspace journals
    ./workspace.py export <name> <dest>      Export a workspace for sharing

Run without arguments to see available commands.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


# ANSI colors
class Colors:
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


# =============================================================================
# SETUP command
# =============================================================================

STARTER_SETTINGS = {
    "permissions": {
        "allow": ["Read", "Edit", "Write", "WebSearch"]
    }
}

CLAUDE_MD_TEMPLATE = '''# {name}

{description}

## Workspace Structure

This is a **workspace** - a folder grouping related repos for coordinated work.

- `repos/` - Git clones and symlinks (gitignored, not tracked here)
- `plans/` - Design documents and implementation plans
- `progress.md` - AI session logs
- `journal.md` - Human work log

**File locations:** All plans and progress go in THIS folder (workspace root), never inside `repos/` subdirectories.

## Repositories

{repos_list}
'''


def setup_claude_symlinks(workspace_path: Path):
    """Create symlinks to parent .claude agents and skills as 'core' subdirectories"""
    parent_claude = Path(".claude")
    workspace_claude = workspace_path / ".claude"

    if not parent_claude.exists():
        print("Warning: Parent .claude directory not found, skipping symlink setup")
        return

    workspace_claude.mkdir(exist_ok=True)
    (workspace_claude / "agents").mkdir(exist_ok=True)
    (workspace_claude / "skills").mkdir(exist_ok=True)

    agents_core = workspace_claude / "agents" / "core"
    if not agents_core.exists() and (parent_claude / "agents").exists():
        agents_core.symlink_to("../../../.claude/agents")
        print(f"  ✓ Linked agents/core -> ../../../.claude/agents")

    skills_core = workspace_claude / "skills" / "core"
    if not skills_core.exists() and (parent_claude / "skills").exists():
        skills_core.symlink_to("../../../.claude/skills")
        print(f"  ✓ Linked skills/core -> ../../../.claude/skills")

    settings_file = workspace_claude / "settings.local.json"
    if not settings_file.exists():
        with open(settings_file, "w") as f:
            json.dump(STARTER_SETTINGS, f, indent=2)
            f.write("\n")
        print(f"  ✓ Created settings.local.json with starter permissions")


def cmd_setup(args):
    """Setup repos for a workspace based on workspace.toml"""
    workspace_path = Path(args.workspace)

    if not workspace_path.exists():
        print(f"Error: Workspace '{args.workspace}' not found")
        sys.exit(1)

    workspace_toml = workspace_path / "workspace.toml"
    if not workspace_toml.exists():
        print(f"Error: workspace.toml not found in {args.workspace}")
        sys.exit(1)

    with open(workspace_toml, "rb") as f:
        config = tomllib.load(f)

    if "repos" not in config:
        print("Error: No 'repos' section found in workspace.toml")
        sys.exit(1)

    repos_dir = workspace_path / "repos"
    repos_dir.mkdir(exist_ok=True)

    # Create plans/ directory
    plans_dir = workspace_path / "plans"
    if not plans_dir.exists():
        plans_dir.mkdir()
        print(f"✓ Created plans/")

    # Create CLAUDE.md from template if it doesn't exist
    claude_md = workspace_path / "CLAUDE.md"
    if not claude_md.exists():
        name = config.get("name", args.workspace)
        description = config.get("description", "[Description of this workspace]")

        # Build repos list
        repos_lines = []
        for repo in config.get("repos", []):
            repo_path = repo.get("path", "")
            repo_name = Path(repo_path).name if repo_path else "unknown"
            repos_lines.append(f"- `{repo_name}` - [description]")
        repos_list = "\n".join(repos_lines) if repos_lines else "- (no repositories yet)"

        content = CLAUDE_MD_TEMPLATE.format(
            name=name,
            description=description,
            repos_list=repos_list
        )
        claude_md.write_text(content)
        print(f"✓ Created CLAUDE.md from template")

    print("\nSetting up .claude symlinks...")
    setup_claude_symlinks(workspace_path)

    print("\nSetting up repositories...")
    for repo in config["repos"]:
        path = Path(repo["path"])
        target_path = workspace_path / path

        if target_path.exists() or target_path.is_symlink():
            print(f"✓ {path} already exists")
            continue

        if source := repo.get("source"):
            source_path = Path(source).expanduser().resolve()
            if not source_path.exists():
                print(f"✗ {path}: source {source} doesn't exist")
                continue
            target_path.symlink_to(source_path)
            print(f"✓ Linked {path} -> {source}")
            continue

        if remote := repo.get("remote"):
            try:
                subprocess.run(
                    ["git", "clone", remote, str(target_path)],
                    check=True, capture_output=True
                )
                print(f"✓ Cloned {remote} -> {path}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to clone {remote}: {e.stderr.decode()}")
            continue

        print(f"⊘ {path} has no remote or source, skipping")

    print(f"\nWorkspace '{args.workspace}' is ready!")


# =============================================================================
# CHECK command
# =============================================================================

def run_git(repo_path: Path, *args) -> tuple[bool, str]:
    """Run a git command and return (success, output)"""
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo_path, capture_output=True, text=True
        )
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def check_repo(repo_path: Path, fetch: bool = False) -> dict:
    """Check a git repo for uncommitted/unpushed changes"""
    result = {"is_git_repo": False, "uncommitted": "", "outgoing": "", "incoming": ""}

    if not (repo_path / ".git").exists():
        return result

    result["is_git_repo"] = True

    success, output = run_git(repo_path, "status", "--porcelain")
    if success:
        result["uncommitted"] = output

    if fetch:
        run_git(repo_path, "fetch", "--quiet")

    success, output = run_git(repo_path, "log", "@{u}..", "--oneline")
    if success:
        result["outgoing"] = output

    success, output = run_git(repo_path, "log", "..@{u}", "--oneline")
    if success:
        result["incoming"] = output

    return result


def check_workspace(workspace_path: Path, fetch: bool = False) -> tuple[int, int]:
    """Check all repos in a workspace. Returns (clean_count, dirty_count)"""
    repos_path = workspace_path / "repos"

    if not repos_path.exists():
        return 0, 0

    ws_name = workspace_path.name
    print(f"{Colors.BLUE}=== Workspace: {ws_name} ==={Colors.RESET}")

    clean, dirty = 0, 0

    for repo in sorted(repos_path.iterdir()):
        if not repo.is_dir():
            continue

        status = check_repo(repo, fetch)
        if not status["is_git_repo"]:
            continue

        has_issues = any([status["uncommitted"], status["outgoing"], status["incoming"]])

        if has_issues:
            print(f"{Colors.CYAN}{repo}{Colors.RESET}")
            dirty += 1
        else:
            clean += 1

        if status["uncommitted"]:
            print("   Uncommitted changes:")
            for line in status["uncommitted"].split("\n"):
                print(f"{Colors.YELLOW}      {line}{Colors.RESET}")

        if status["outgoing"]:
            print("   Outgoing commits (not pushed):")
            for line in status["outgoing"].split("\n"):
                print(f"{Colors.GREEN}      {line}{Colors.RESET}")

        if status["incoming"]:
            print("   Incoming commits (not pulled):")
            for line in status["incoming"].split("\n"):
                print(f"{Colors.RED}      {line}{Colors.RESET}")

    print()
    return clean, dirty


def find_workspaces(base_path: Path) -> list[Path]:
    """Find all workspace directories (those with repos/ folder)"""
    workspaces = []
    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith(".") and (item / "repos").is_dir():
            workspaces.append(item)
    return sorted(workspaces)


def cmd_check(args):
    """Check workspaces for uncommitted/unpushed git changes"""
    cwd = Path.cwd().resolve()
    in_workspace = (cwd / "repos").is_dir()

    print(f"{Colors.BLUE}Checking workspaces for git changes...{Colors.RESET}")
    if args.fetch:
        print(f"{Colors.YELLOW}(fetching from remotes){Colors.RESET}")
    print()

    total_clean, total_dirty = 0, 0

    if args.workspace:
        ws_path = cwd / args.workspace
        if not ws_path.exists():
            print(f"{Colors.RED}Workspace not found: {args.workspace}{Colors.RESET}")
            sys.exit(1)
        if not (ws_path / "repos").is_dir():
            print(f"{Colors.RED}Not a workspace (no repos/ folder): {args.workspace}{Colors.RESET}")
            sys.exit(1)
        clean, dirty = check_workspace(ws_path, args.fetch)
        total_clean, total_dirty = clean, dirty
    elif in_workspace:
        clean, dirty = check_workspace(cwd, args.fetch)
        total_clean, total_dirty = clean, dirty
    else:
        workspaces = find_workspaces(cwd)
        if not workspaces:
            print("No workspaces found")
            sys.exit(0)
        for ws_path in workspaces:
            clean, dirty = check_workspace(ws_path, args.fetch)
            total_clean += clean
            total_dirty += dirty

    print(f"{Colors.GREEN}Clean repos:{Colors.RESET} {total_clean} | "
          f"{Colors.RED}Repos with changes:{Colors.RESET} {total_dirty}")


# =============================================================================
# LINK command
# =============================================================================

def cmd_link(args):
    """Link Obsidian notes with workspace frontmatter to their workspaces"""
    vault = Path("../Notes/notes").expanduser()
    workspaces_dir = Path(__file__).parent.resolve()
    aibrief_dir = Path.home() / "Dropbox/Apps/work-journal-reviewer"

    if not vault.exists():
        print(f"{Colors.RED}Vault not found: {vault}{Colors.RESET}")
        sys.exit(1)

    # Create aibrief folder if Dropbox Apps exists
    if (Path.home() / "Dropbox/Apps").exists():
        aibrief_dir.mkdir(parents=True, exist_ok=True)

    # Find all notes with workspace frontmatter
    try:
        result = subprocess.run(
            ["grep", "-rl", "^workspace: ", str(vault)],
            capture_output=True, text=True
        )
        notes = [Path(p) for p in result.stdout.strip().split("\n") if p]
    except Exception as e:
        print(f"{Colors.RED}Error searching vault: {e}{Colors.RESET}")
        sys.exit(1)

    for note in notes:
        # Extract workspace name from frontmatter
        workspace = None
        with open(note) as f:
            for line in f:
                if line.startswith("workspace: "):
                    workspace = line.split("workspace: ")[1].strip()
                    break

        if not workspace:
            continue

        # Determine workspace directory
        workspace_dir = workspaces_dir / workspace
        link_path = workspace_dir / "journal.md"
        aibrief_link = aibrief_dir / f"{workspace}.md"

        # Link to workspace folder
        if not workspace_dir.is_dir():
            print(f"- {workspace} (no workspace folder)")
        elif link_path.is_symlink():
            print(f"✓ {workspace} (already linked)")
        elif link_path.exists():
            print(f"✗ {workspace} (journal.md exists but is not a symlink)")
        else:
            link_path.symlink_to(note.resolve())
            print(f"✓ {workspace} → {note}")

        # Hard link to aibrief folder (symlinks don't work with Dropbox API)
        if aibrief_dir.is_dir():
            if aibrief_link.exists():
                aibrief_link.unlink()
            try:
                aibrief_link.hardlink_to(note.resolve())
                print(f"  + aibrief: {workspace}.md (hard linked)")
            except OSError:
                # Hard links may fail across filesystems
                pass


# =============================================================================
# EXPORT command
# =============================================================================

def cmd_export(args):
    """Export a workspace to an external location for sharing"""
    workspace_path = Path(args.workspace)
    export_path = Path(args.destination).expanduser().resolve()

    if not workspace_path.exists():
        print(f"{Colors.RED}Error: Workspace '{args.workspace}' not found{Colors.RESET}")
        sys.exit(1)

    workspace_toml = workspace_path / "workspace.toml"
    if not workspace_toml.exists():
        print(f"{Colors.RED}Error: workspace.toml not found in {args.workspace}{Colors.RESET}")
        sys.exit(1)

    # Create export directory
    export_path.mkdir(parents=True, exist_ok=True)
    print(f"Exporting to: {export_path}")

    # Copy workspace.py
    script_path = Path(__file__).resolve()
    dest_script = export_path / "workspace.py"
    shutil.copy2(script_path, dest_script)
    dest_script.chmod(0o755)
    print(f"✓ Copied workspace.py")

    # Copy root CLAUDE.md and README.md
    root_dir = Path(__file__).parent
    for filename in ["CLAUDE.md", "README.md"]:
        src = root_dir / filename
        if src.exists():
            shutil.copy2(src, export_path / filename)
            print(f"✓ Copied {filename}")
        else:
            print(f"⊘ No root {filename} found")

    # Copy root .claude/agents and .claude/skills directories
    src_claude_dir = root_dir / ".claude"
    dest_claude_dir = export_path / ".claude"
    dest_claude_dir.mkdir(exist_ok=True)
    for subdir in ["agents", "skills"]:
        src_dir = src_claude_dir / subdir
        dest_dir = dest_claude_dir / subdir
        if src_dir.exists() and src_dir.is_dir():
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(src_dir, dest_dir)
            count = len(list(dest_dir.iterdir()))
            print(f"✓ Copied .claude/{subdir}/ ({count} items)")
        else:
            dest_dir.mkdir(exist_ok=True)
            print(f"✓ Created .claude/{subdir}/ (empty)")

    # Create workspace subdirectory
    ws_export = export_path / args.workspace
    ws_export.mkdir(exist_ok=True)

    # Copy workspace.toml
    shutil.copy2(workspace_toml, ws_export / "workspace.toml")
    print(f"✓ Copied {args.workspace}/workspace.toml")

    # Copy workspace CLAUDE.md if exists
    ws_claude = workspace_path / "CLAUDE.md"
    if ws_claude.exists():
        shutil.copy2(ws_claude, ws_export / "CLAUDE.md")
        print(f"✓ Copied {args.workspace}/CLAUDE.md")

    # Copy plans/ directory if exists
    ws_plans = workspace_path / "plans"
    if ws_plans.exists() and ws_plans.is_dir():
        dest_plans = ws_export / "plans"
        if dest_plans.exists():
            shutil.rmtree(dest_plans)
        shutil.copytree(ws_plans, dest_plans)
        print(f"✓ Copied {args.workspace}/plans/")

    # Copy workspace .claude/agents and .claude/skills (skip symlinks like 'core')
    ws_claude = workspace_path / ".claude"
    if ws_claude.exists():
        dest_claude = ws_export / ".claude"
        dest_claude.mkdir(exist_ok=True)
        for subdir in ["agents", "skills"]:
            src_dir = ws_claude / subdir
            if src_dir.exists() and src_dir.is_dir():
                dest_dir = dest_claude / subdir
                dest_dir.mkdir(exist_ok=True)
                copied = 0
                for item in src_dir.iterdir():
                    if not item.is_symlink():  # Skip 'core' symlinks
                        dest_item = dest_dir / item.name
                        if item.is_dir():
                            if dest_item.exists():
                                shutil.rmtree(dest_item)
                            shutil.copytree(item, dest_item)
                        else:
                            shutil.copy2(item, dest_item)
                        copied += 1
                if copied:
                    print(f"✓ Copied {copied} items from {args.workspace}/.claude/{subdir}/")

    # Note about source entries
    with open(workspace_toml, "rb") as f:
        config = tomllib.load(f)

    source_entries = [r for r in config.get("repos", []) if r.get("source")]
    if source_entries:
        print(f"\n{Colors.YELLOW}Note: This workspace has {len(source_entries)} local source entries.{Colors.RESET}")
        print("Recipients will need to update these paths in workspace.toml:")
        for entry in source_entries:
            print(f"  - {entry['path']}: {entry.get('source')}")

    print(f"\n{Colors.GREEN}Export complete!{Colors.RESET}")
    print(f"To set up: cd {export_path} && ./workspace.py setup {args.workspace}")


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Workspace management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.BOLD}Commands:{Colors.RESET}
  {Colors.CYAN}setup{Colors.RESET} <name>              Setup a workspace (clone repos, create symlinks)
  {Colors.CYAN}gitcheck{Colors.RESET} [name]           Check for uncommitted/unpushed git changes
  {Colors.CYAN}link{Colors.RESET}                      Link Obsidian notes to workspace journals
  {Colors.CYAN}export{Colors.RESET} <name> <dest>      Export a workspace for sharing

{Colors.BOLD}Examples:{Colors.RESET}
  ./workspace.py setup webdev              # Setup the webdev workspace
  ./workspace.py gitcheck                  # Check all workspaces for changes
  ./workspace.py gitcheck refgenie         # Check specific workspace
  ./workspace.py gitcheck -f               # Fetch from remotes first
  ./workspace.py link                      # Link Obsidian notes to journals
  ./workspace.py export pepkit ~/shared    # Export pepkit workspace to ~/shared
"""
    )

    subparsers = parser.add_subparsers(dest="command", title="commands")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Setup a workspace")
    setup_parser.add_argument("workspace", help="Workspace directory name")

    # gitcheck command
    check_parser = subparsers.add_parser("gitcheck", help="Check for git changes")
    check_parser.add_argument("workspace", nargs="?", help="Specific workspace (optional)")
    check_parser.add_argument("-f", "--fetch", action="store_true", help="Fetch from remotes first")

    # link command
    subparsers.add_parser("link", help="Link Obsidian notes to journals")

    # export command
    export_parser = subparsers.add_parser("export", help="Export a workspace for sharing")
    export_parser.add_argument("workspace", help="Workspace directory name")
    export_parser.add_argument("destination", help="Destination path for export")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "gitcheck":
        cmd_check(args)
    elif args.command == "link":
        cmd_link(args)
    elif args.command == "export":
        cmd_export(args)


if __name__ == "__main__":
    main()
