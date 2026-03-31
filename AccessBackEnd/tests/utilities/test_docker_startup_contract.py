from pathlib import Path


def test_dockerfile_uses_python_runner_for_startup():
    dockerfile = Path(__file__).resolve().parents[3] / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")

    assert 'CMD ["python3", "/app/scripts/docker/dev_stack_runner.py"]' in content


def test_compose_does_not_override_startup_command():
    compose = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "command:" not in content
