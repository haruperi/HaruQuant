"""Documentation file management routes."""

import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# Define the root directory for documentation
# Go up two levels from apps/api/routes to reach apps/api, then up to root, then to docs
DOCS_ROOT = Path(__file__).parent.parent.parent.parent / "docs"
CONTENT_PATH_QUERY = Query(..., description="Relative path to the file")


class FileNode(BaseModel):
    """Tree node representing a documentation file or directory."""

    name: str
    path: str
    type: str  # 'file' or 'directory'
    children: Optional[List["FileNode"]] = None


class SaveFileRequest(BaseModel):
    """Request payload for saving a documentation file."""

    path: str
    content: str


def get_directory_structure(root_dir: Path, relative_path: str = "") -> List[FileNode]:
    """Return a tree structure for markdown files under a root directory."""
    items: List[FileNode] = []
    if not root_dir.exists():
        return items

    for item in sorted(os.listdir(root_dir)):
        # Ignore hidden files/dirs and image folder for now if needed, but showing everything is fine
        if item.startswith("."):
            continue

        full_path = root_dir / item
        item_relative_path = os.path.join(relative_path, item).replace(
            "\\", "/"
        )  # Ensure forward slashes

        if full_path.is_dir():
            items.append(
                FileNode(
                    name=item,
                    path=item_relative_path,
                    type="directory",
                    children=get_directory_structure(full_path, item_relative_path),
                )
            )
        else:
            if item.endswith(".md"):
                items.append(FileNode(name=item, path=item_relative_path, type="file"))
    return items


def validate_path(request_path: str) -> Path:
    """Validate and resolve a path within the docs root."""
    # Remove leading slash if present
    if request_path.startswith("/"):
        request_path = request_path[1:]

    # Prevent path traversal
    if ".." in request_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    full_path = (DOCS_ROOT / request_path).resolve()

    # Ensure the resolved path is within DOCS_ROOT
    if not str(full_path).startswith(str(DOCS_ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    return full_path


@router.get("/files", response_model=List[FileNode])
async def get_files():
    """Get the tree structure of the documentation directory."""
    try:
        if not DOCS_ROOT.exists():
            os.makedirs(DOCS_ROOT, exist_ok=True)
        return get_directory_structure(DOCS_ROOT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def get_content(path: str = CONTENT_PATH_QUERY):
    """Read the content of a markdown file."""
    try:
        full_path = validate_path(path)

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        content = full_path.read_text(encoding="utf-8")
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_file(request: SaveFileRequest):
    """Save content to a markdown file. Creates directories if they don't exist."""
    try:
        full_path = validate_path(request.path)

        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(request.content, encoding="utf-8")
        return {"status": "success", "path": request.path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_file(path: str = CONTENT_PATH_QUERY):
    """Delete a markdown file."""
    try:
        full_path = validate_path(path)

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if full_path.is_dir():
            raise HTTPException(
                status_code=400, detail="Cannot delete directory directly"
            )

        os.remove(full_path)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
