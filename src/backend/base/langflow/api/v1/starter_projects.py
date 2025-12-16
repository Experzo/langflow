import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from langflow.services.auth.utils import get_current_active_user

router = APIRouter(prefix="/starter-projects", tags=["Flows"])

# Get the path to the starter_projects directory
STARTER_PROJECTS_DIR = Path(__file__).parent.parent.parent / "initial_setup" / "starter_projects"

# Category mapping based on template name keywords
CATEGORY_MAPPING = {
    "Basic Prompting": ("Getting Started", "Beginner"),
    "Basic Prompt Chaining": ("Getting Started", "Beginner"),
    "Memory Chatbot": ("Chatbots", "Intermediate"),
    "Simple Agent": ("AI Agents", "Intermediate"),
    "Document Q&A": ("RAG", "Intermediate"),
    "Vector Store RAG": ("RAG", "Advanced"),
    "Hybrid Search RAG": ("RAG", "Advanced"),
    "Knowledge Ingestion": ("RAG", "Intermediate"),
    "Knowledge Retrieval": ("RAG", "Intermediate"),
    "Blog Writer": ("Content Generation", "Intermediate"),
    "Twitter Thread Generator": ("Content Generation", "Intermediate"),
    "Instagram Copywriter": ("Content Generation", "Intermediate"),
    "SEO Keyword Generator": ("Content Generation", "Intermediate"),
    "Research Agent": ("AI Agents", "Advanced"),
    "Search agent": ("AI Agents", "Intermediate"),
    "Social Media Agent": ("AI Agents", "Intermediate"),
    "Travel Planning Agents": ("AI Agents", "Advanced"),
    "Sequential Tasks Agents": ("AI Agents", "Advanced"),
    "Market Research": ("Business", "Intermediate"),
    "Financial Report Parser": ("Business", "Advanced"),
    "Invoice Summarizer": ("Business", "Intermediate"),
    "SaaS Pricing": ("Business", "Intermediate"),
    "Price Deal Finder": ("Business", "Intermediate"),
    "Meeting Summary": ("Productivity", "Beginner"),
    "News Aggregator": ("Productivity", "Intermediate"),
    "Youtube Analysis": ("Data Analysis", "Intermediate"),
    "Text Sentiment Analysis": ("Data Analysis", "Beginner"),
    "Image Sentiment Analysis": ("Data Analysis", "Intermediate"),
    "Custom Component Generator": ("Development", "Advanced"),
    "Portfolio Website Code Generator": ("Development", "Advanced"),
    "Research Translation Loop": ("AI Agents", "Advanced"),
    "Pokédex Agent": ("AI Agents", "Intermediate"),
    "Nvidia Remix": ("AI Agents", "Advanced"),
}

# Icon mapping based on category
CATEGORY_ICONS = {
    "Getting Started": "sparkles",
    "Chatbots": "message-circle",
    "AI Agents": "bot",
    "RAG": "database",
    "Content Generation": "pen-tool",
    "Business": "briefcase",
    "Productivity": "clipboard",
    "Data Analysis": "bar-chart",
    "Development": "code",
}


def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


# Pydantic models for API schema compatibility
class ViewPort(BaseModel):
    x: float
    y: float
    zoom: float


class NodeData(BaseModel):
    # This is a simplified version - the actual NodeData has many more fields
    # but we only need the basic structure for the API schema
    model_config = {"extra": "allow"}  # Allow extra fields


class EdgeData(BaseModel):
    # This is a simplified version - the actual EdgeData has many more fields
    # but we only need the basic structure for the API schema
    model_config = {"extra": "allow"}  # Allow extra fields


class GraphData(BaseModel):
    nodes: list[dict[str, Any]]  # Use dict to be flexible with the complex NodeData structure
    edges: list[dict[str, Any]]  # Use dict to be flexible with the complex EdgeData structure
    viewport: ViewPort | None = None


class GraphDumpResponse(BaseModel):
    data: GraphData
    is_component: bool | None = None
    name: str | None = None
    description: str | None = None
    endpoint_name: str | None = None


class StarterProjectTemplate(BaseModel):
    """A starter project template with metadata for the gallery UI."""

    id: str
    name: str
    description: str
    category: str
    difficulty: str  # "Beginner", "Intermediate", "Advanced"
    icon: str
    node_count: int
    edge_count: int
    tags: list[str]
    data: GraphData


class StarterProjectTemplatesResponse(BaseModel):
    """Response containing all starter project templates."""

    templates: list[StarterProjectTemplate]
    total: int


@router.get("/templates", dependencies=[Depends(get_current_active_user)], status_code=200)
async def get_all_starter_project_templates() -> StarterProjectTemplatesResponse:
    """Get all starter project templates from JSON files.

    This endpoint reads all JSON files from the starter_projects directory
    and returns them with enriched metadata for the template gallery UI.
    """
    templates: list[StarterProjectTemplate] = []

    if not STARTER_PROJECTS_DIR.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Starter projects directory not found: {STARTER_PROJECTS_DIR}",
        )

    json_files = sorted(STARTER_PROJECTS_DIR.glob("*.json"))

    for json_file in json_files:
        try:
            with json_file.open(encoding="utf-8") as f:
                raw_data = json.load(f)

            # Extract name from JSON or filename
            filename_name = json_file.stem  # e.g., "Basic Prompting"
            template_name = raw_data.get("name") or filename_name

            # Extract description
            description = raw_data.get("description", "")
            if not description:
                # Generate a default description based on name
                description = f"A {template_name.lower()} template to help you get started."

            # Get category and difficulty from mapping
            category_info = CATEGORY_MAPPING.get(filename_name, ("Other", "Intermediate"))
            category, difficulty = category_info

            # Get icon based on category
            icon = CATEGORY_ICONS.get(category, "file")

            # Extract flow data - handle both formats
            if "data" in raw_data and isinstance(raw_data["data"], dict):
                flow_data = raw_data["data"]
            else:
                # The raw_data itself might be the flow data
                flow_data = raw_data

            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            viewport = flow_data.get("viewport")

            # Generate tags from node types
            node_types = set()
            for node in nodes:
                if "data" in node and "type" in node["data"]:
                    node_types.add(node["data"]["type"])
                elif "type" in node:
                    node_types.add(node["type"])
            tags = list(node_types)[:5]  # Limit to 5 tags

            # Create GraphData
            graph_data = GraphData(
                nodes=nodes,
                edges=edges,
                viewport=viewport,
            )

            # Create template
            template = StarterProjectTemplate(
                id=slugify(filename_name),
                name=template_name,
                description=description,
                category=category,
                difficulty=difficulty,
                icon=icon,
                node_count=len(nodes),
                edge_count=len(edges),
                tags=tags,
                data=graph_data,
            )
            templates.append(template)

        except json.JSONDecodeError as e:
            # Log but continue with other files
            print(f"Warning: Failed to parse {json_file.name}: {e}")
            continue
        except Exception as e:
            # Log but continue with other files
            print(f"Warning: Error processing {json_file.name}: {e}")
            continue

    return StarterProjectTemplatesResponse(templates=templates, total=len(templates))


@router.get("/", dependencies=[Depends(get_current_active_user)], status_code=200)
async def get_starter_projects() -> list[GraphDumpResponse]:
    """Get a list of starter projects."""
    from langflow.initial_setup.load import get_starter_projects_dump

    try:
        # Get the raw data from lfx GraphDump
        raw_data = get_starter_projects_dump()

        # Convert TypedDict GraphDump to Pydantic GraphDumpResponse
        results = []
        for item in raw_data:
            # Create GraphData
            graph_data = GraphData(
                nodes=item.get("data", {}).get("nodes", []),
                edges=item.get("data", {}).get("edges", []),
                viewport=item.get("data", {}).get("viewport"),
            )

            # Create GraphDumpResponse
            graph_dump = GraphDumpResponse(
                data=graph_data,
                is_component=item.get("is_component"),
                name=item.get("name"),
                description=item.get("description"),
                endpoint_name=item.get("endpoint_name"),
            )
            results.append(graph_dump)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return results
