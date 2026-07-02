from pathlib import Path


def test_legacy_model_nodes_are_removed():
    nodes_dir = Path(__file__).resolve().parents[1] / "src" / "nodes"

    assert not (nodes_dir / "planner.py").exists()
    assert not (nodes_dir / "coder.py").exists()
    assert not (nodes_dir / "tester.py").exists()
    assert not (nodes_dir / "reviewer.py").exists()
