#!/usr/bin/env python3
"""Mark plan complete: add timestamp to frontmatter and move to completed folder."""
import sys, re
from datetime import datetime
from pathlib import Path

def mark_completed(filepath: str) -> None:
    path = Path(filepath)
    content = path.read_text()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if content.startswith("---"):
        # Update existing frontmatter - add completed field
        end = content.index("---", 3)
        fm = content[4:end]
        # Update modified and add completed
        fm = re.sub(r"modified:.*", f"modified: {now}", fm)
        if "completed:" not in fm:
            fm = fm.rstrip() + f"\ncompleted: {now}\n"
        else:
            fm = re.sub(r"completed:.*", f"completed: {now}", fm)
        content = f"---\n{fm}---{content[end+3:]}"
    else:
        # Add new frontmatter with completed
        project = path.stem.split("_")[0]
        content = f"---\ncreated: {now}\nmodified: {now}\ncompleted: {now}\nproject: {project}\n---\n\n{content}"

    # Move to completed subfolder
    completed_dir = path.parent / "completed"
    completed_dir.mkdir(exist_ok=True)
    new_path = completed_dir / path.name
    new_path.write_text(content)
    path.unlink()
    print(f"Moved to {new_path}")

if __name__ == "__main__":
    mark_completed(sys.argv[1])
