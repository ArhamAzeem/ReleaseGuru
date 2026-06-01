# ReleaseGuru

ReleaseGuru is an AI release assistant CLI for git repositories.

Main feature: turn commit history into a release plan that tells the team what changed, what matters, what to test, and what can be published.

Secondary helpers: version bumping, release notes, GitHub Releases, JSON output, and GitHub Actions outputs.

## Features

- AI release brief from git commits
- Release summary, highlights, risks, checks, and user-facing notes
- SemVer recommendation: `major`, `minor`, or `patch`
- Auto-version from latest git tag
- Manual version override
- Markdown or JSON output
- Notes-only mode for GitHub release bodies
- Dry-run mode for CI and review
- GitHub Release publish
- Draft and prerelease publish modes
- GitHub repo override with `--github-repo`
- Optional tag creation and push
- GitHub Actions output support with `--ci-output`
- Multi-provider support: Groq, Gemini, OpenAI, Anthropic, xAI

## Install

After PyPI publish:

```bash
pipx install releaseguru
```

Or:

```bash
pip install releaseguru
```

During local development:

```bash
cd ReleaseGuru
python -m venv venv
pip install -e .
cp .env.example .env
```

Add one AI provider key to `.env`.

```env
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
XAI_API_KEY=
GITHUB_TOKEN=
```

`GITHUB_TOKEN` is only needed when publishing.

## Basic Use

Generate release plan:

```bash
releaseguru
```

Use custom range:

```bash
releaseguru --from v1.2.0 --to HEAD
```

Save to file:

```bash
releaseguru --output RELEASE.md
```

Generate JSON for automation:

```bash
releaseguru --format json --output release.json
```

Only print release notes:

```bash
releaseguru --notes-only
```

Dry run publish flow:

```bash
releaseguru --publish --dry-run --github-repo owner/repo
```

Publish full release:

```bash
releaseguru --publish
```

Publish only notes body:

```bash
releaseguru --publish --notes-only
```

Publish draft:

```bash
releaseguru --publish --draft
```

Publish prerelease:

```bash
releaseguru --publish --prerelease
```

Publish without creating/pushing a local tag:

```bash
releaseguru --publish --skip-tag
```

## GitHub Actions

Use this when you want manual release from Actions.

```yaml
name: ReleaseGuru

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ReleaseGuru
        run: pip install releaseguru
      - name: Create release
        id: releaseguru
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: releaseguru --publish --notes-only --ci-output

      - name: Show result
        run: |
          echo "Version: ${{ steps.releaseguru.outputs.version }}"
          echo "Bump: ${{ steps.releaseguru.outputs.bump_type }}"
          echo "URL: ${{ steps.releaseguru.outputs.release_url }}"
```

For review before publishing:

```yaml
- name: Preview release
  env:
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
  run: releaseguru --dry-run --format json --output release.json
```

## Testing

Syntax check:

```bash
python -m py_compile releaseguru/cli.py releaseguru/providers.py
```

Unit tests:

```bash
python -m unittest discover -s tests
```

CLI dry run with mocked AI response:

```bash
releaseguru --mock-response tests/fixtures/ai_response.txt --dry-run
```

Real AI test:

```bash
releaseguru --provider groq --dry-run
```

Real GitHub publish test:

```bash
releaseguru --provider groq --publish --draft
```

Use `--draft` first so you can inspect the release before making it public.

## Release Ways

- Local preview: `releaseguru --dry-run`
- Local file: `releaseguru --output RELEASE.md`
- CI preview: `releaseguru --format json --ci-output`
- GitHub draft: `releaseguru --publish --draft`
- GitHub prerelease: `releaseguru --publish --prerelease`
- GitHub stable release: `releaseguru --publish`
- Notes-only release body: `releaseguru --publish --notes-only`
- Existing tag release: `releaseguru --publish --skip-tag --version v1.2.3`
- Manual version release: `releaseguru --version v2.0.0 --publish`

## Publish To PyPI

Build package:

```bash
python -m pip install --upgrade build twine
python -m build
```

Check package:

```bash
python -m twine check dist/*
```

Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI:

```bash
pipx install --index-url https://test.pypi.org/simple/ --pip-args="--extra-index-url https://pypi.org/simple/" releaseguru
```

Upload to real PyPI:

```bash
python -m twine upload dist/*
```

GitHub Actions publishing is also included in `.github/workflows/publish-pypi.yml`.
For tokenless publishing, configure PyPI Trusted Publishing for this repository and publish a GitHub Release.

## Provider Defaults

| Provider | Option | Default model |
|---|---|---|
| Groq | `--provider groq` | `llama-3.3-70b-versatile` |
| Gemini | `--provider gemini` | `gemini-1.5-flash` |
| OpenAI | `--provider openai` | `gpt-4o-mini` |
| Anthropic | `--provider anthropic` | `claude-3-5-haiku-20241022` |
| xAI | `--provider xai` | `grok-3-mini` |
