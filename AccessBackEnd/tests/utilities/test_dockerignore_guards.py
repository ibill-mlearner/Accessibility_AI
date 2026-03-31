from pathlib import Path


def test_dockerignore_uses_default_deny_allowlist_strategy():
    dockerignore = Path(__file__).resolve().parents[3] / '.dockerignore'
    content = dockerignore.read_text(encoding='utf-8')

    assert content.splitlines()[1].strip() == '**'
    assert '!AccessBackEnd/app/**' in content
    assert '!AccessAppFront/src/**' in content
    assert '!scripts/docker/dev_stack_runner.py' in content
