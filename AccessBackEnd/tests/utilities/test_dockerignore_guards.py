from pathlib import Path


def test_dockerignore_blocks_large_node_context_entries():
    dockerignore = Path(__file__).resolve().parents[3] / ".dockerignore"
    content = dockerignore.read_text(encoding="utf-8")

    assert "**/node_modules/" in content
    assert "**/accessibility-ai-workspace" in content
