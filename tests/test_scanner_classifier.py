from src.indexer.classifier import classify_path
from src.indexer.scanner import compute_content_hash, scan_project


def test_classify_path_recognizes_project_file_types():
    assert classify_path("src/map_data/sea_route.cpp") == ("source", "cpp")
    assert classify_path("src/map_data/sea_route.h") == ("header", "cpp")
    assert classify_path("doc/readme.md") == ("doc", "markdown")
    assert classify_path("doc/chase.txt") == ("doc", "text")
    assert classify_path("CMakeLists.txt") == ("build_config", "cmake")
    assert classify_path("linux_prj/build.sh") == ("script", "shell")
    assert classify_path("linux_prj/config.ini") == ("config", "ini")
    assert classify_path("project.AFCfile") == ("config", "afc")


def test_scan_project_includes_relevant_files_and_skips_build_outputs(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src/map_data").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "linux_prj").mkdir()
    (project / "build").mkdir()

    (project / "src/map_data/sea_route.cpp").write_text("int route() { return 1; }", encoding="utf-8")
    (project / "src/map_data/sea_route.h").write_text("int route();", encoding="utf-8")
    (project / "doc/readme.md").write_text("# readme", encoding="utf-8")
    (project / "linux_prj/build.sh").write_text("#!/bin/bash", encoding="utf-8")
    (project / "build/generated.cpp").write_text("int generated;", encoding="utf-8")
    (project / "libx.so").write_bytes(b"binary")

    files = scan_project(project)
    paths = {f.path for f in files}

    assert "src/map_data/sea_route.cpp" in paths
    assert "src/map_data/sea_route.h" in paths
    assert "doc/readme.md" in paths
    assert "linux_prj/build.sh" in paths
    assert "build/generated.cpp" not in paths
    assert "libx.so" not in paths

    route_file = next(f for f in files if f.path == "src/map_data/sea_route.cpp")
    assert route_file.file_type == "source"
    assert route_file.language == "cpp"
    assert route_file.content_hash == compute_content_hash(project / "src/map_data/sea_route.cpp")
