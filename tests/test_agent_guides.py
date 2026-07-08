from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agent_guides_exist_and_reference_project_entrypoints():
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "scripts/ask_project.py" in agents
    assert "assistant" in agents
    assert "indexer" in agents
    assert "README.md" in agents
    assert "Do not read `README.md` by default" in agents
    assert "docs/superpowers/history/" in agents
    assert "AGENTS.md" in claude
    assert "Do not read `README.md` by default" in claude


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


def test_agent_guide_documents_english_default_language_policy():
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "English by default" in agents
    assert "Use Chinese only when the user explicitly requests Chinese" in agents
    assert "Final user-facing answers must be Chinese" not in agents


def test_agent_guide_routes_project_skills_and_current_date_history():
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "config/skills/" in agents
    assert "config/skills/langgraph-fundamentals/SKILL.md" in agents
    assert "config/skills/langchain-rag/SKILL.md" in agents
    assert "config/skills/swarm/SKILL.md" in agents
    assert "skills-lock.json" in agents
    assert "Use today's date from the session context" in agents
    assert "latest existing history file" in agents
    assert "2026-07-07" not in agents
