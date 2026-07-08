from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agent_guides_exist_and_reference_project_entrypoints():
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "scripts/ask_project.py" in agents
    assert "assistant" in agents
    assert "indexer" in agents
    assert "README.md" in agents
    assert "docs/superpowers/history/" in agents
    assert "AGENTS.md" in claude
    assert "README.md" in claude


def test_agent_workflow_recipe_documents_search_ask_and_safety_boundary():
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    guide_path = PROJECT_ROOT / "docs/superpowers/guides/agent-workflows.md"
    guide = guide_path.read_text(encoding="utf-8")

    assert "docs/superpowers/guides/agent-workflows.md" in agents
    assert "docs/superpowers/guides/agent-workflows.md" in readme
    assert "scripts/search_project.py" in guide
    assert "scripts/ask_project.py" in guide
    assert "Read" in guide
    assert "read-only" in guide
    assert "project_memories" in guide
    assert "research_notes" in guide
