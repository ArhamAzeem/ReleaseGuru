import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click
import requests
from dotenv import load_dotenv

from .providers import PROVIDERS, auto_detect_provider

load_dotenv()


@dataclass
class ReleaseResult:
    version: str
    bump_type: str
    release_brief: str
    release_notes: str
    commit_count: int
    from_ref: str | None
    to_ref: str
    provider: str
    published_url: str | None = None


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def get_commits(from_ref: str | None, to_ref: str) -> list[str]:
    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
    result = run_git(["log", range_spec, "--pretty=format:%s (%an)"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_latest_tag() -> str | None:
    result = run_git(["describe", "--tags", "--abbrev=0"], check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def get_github_repo_slug() -> str | None:
    result = run_git(["remote", "get-url", "origin"], check=False)
    if result.returncode != 0:
        return None

    match = re.search(r"github\.com[:/]([^/]+)/([^.]+)(?:\.git)?", result.stdout.strip())
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def tag_exists(tag_name: str) -> bool:
    return run_git(["rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"], check=False).returncode == 0


def create_and_push_tag(tag_name: str, dry_run: bool) -> None:
    if dry_run:
        return

    if not tag_exists(tag_name):
        run_git(["tag", "-a", tag_name, "-m", f"Release {tag_name}"])

    run_git(["push", "origin", tag_name])


def bump_version(version: str, bump_type: str) -> str:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        return f"{version}-{bump_type}-bump"

    major, minor, patch = map(int, match.groups())
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    prefix = "v" if version.lower().startswith("v") else ""
    return f"{prefix}{major}.{minor}.{patch}"


def build_prompt(commits: list[str], current_version: str) -> str:
    lines = "\n".join(f"- {commit}" for commit in commits)
    return f"""You are a release assistant for software teams.

Analyze the git commits and prepare a release brief for humans. Help the team decide what this release is, what matters most, what needs attention, and what can be published.

You MUST start the response with this exact line:
__RECOMMENDED_BUMP__: <major|minor|patch>

After that, output valid Markdown with these sections in this order:
# Release Assistant Brief
## Release Summary
## Highlights
## Risks & Checks
## Suggested Release Notes

Rules:
- The release summary must be 2 to 4 sentences.
- Highlights must contain 3 to 6 bullets when possible.
- Risks & Checks must focus on validation, regressions, migrations, or rollout concerns.
- Suggested Release Notes must be user-facing and grouped under:
  - ### Features
  - ### Bug Fixes
  - ### Breaking Changes
  - ### Improvements
- Skip empty sections inside Suggested Release Notes.
- Use present tense.
- Avoid internal jargon unless needed for risk explanation.
- Mention breaking changes only when justified by commits.
- Choose major for breaking changes, minor for new visible functionality, patch for fixes/internal improvements only.

Current version context: {current_version}

Commits:
{lines}

Output only the marker line and Markdown."""


def parse_ai_response(ai_raw: str) -> tuple[str, str]:
    bump_type = "patch"
    body_lines: list[str] = []

    for line in ai_raw.splitlines():
        if line.startswith("__RECOMMENDED_BUMP__"):
            match = re.search(r"__RECOMMENDED_BUMP__:\s*(major|minor|patch)", line, re.IGNORECASE)
            if match:
                bump_type = match.group(1).lower()
            continue
        body_lines.append(line)

    return bump_type, "\n".join(body_lines).strip()


def extract_release_notes(release_brief: str) -> str:
    marker = "## Suggested Release Notes"
    if marker not in release_brief:
        return release_brief.strip()
    return release_brief.split(marker, 1)[1].strip()


def build_output_document(result: ReleaseResult) -> str:
    header = [
        f"# Release Plan {result.version}",
        "",
        f"- Recommended bump: `{result.bump_type}`",
        f"- Commits analyzed: `{result.commit_count}`",
        "",
    ]
    return "\n".join(header) + result.release_brief.strip() + "\n"


def publish_github_release(
    repo_slug: str,
    tag_name: str,
    name: str,
    body: str,
    token: str,
    draft: bool,
    prerelease: bool,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"https://github.com/{repo_slug}/releases/tag/{tag_name}"

    url = f"https://api.github.com/repos/{repo_slug}/releases"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": draft,
        "prerelease": prerelease,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code not in (200, 201):
        raise click.ClickException(f"GitHub API error: {response.status_code} - {response.text}")
    return response.json().get("html_url", "")


def write_github_output(result: ReleaseResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    lines = [
        f"version={result.version}",
        f"bump_type={result.bump_type}",
        f"commit_count={result.commit_count}",
    ]
    if result.published_url:
        lines.append(f"release_url={result.published_url}")

    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def render_result(result: ReleaseResult, output_format: str, notes_only: bool) -> str:
    if output_format == "json":
        return json.dumps(asdict(result), indent=2)
    if notes_only:
        return result.release_notes + "\n"
    return build_output_document(result)


def call_provider(provider: str, prompt: str, api_key: str | None, model: str | None, mock_response: str | None) -> str:
    if mock_response:
        return Path(mock_response).read_text(encoding="utf-8")
    return PROVIDERS[provider](prompt, api_key=api_key, model=model)


@click.command()
@click.option("--from", "from_ref", default=None, help="Start tag/ref. Default: latest git tag")
@click.option("--to", "to_ref", default="HEAD", help="End ref. Default: HEAD")
@click.option("--version", default=None, help="Explicit release version")
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["groq", "openai", "anthropic", "gemini", "xai"]),
    help="LLM provider. Default: auto-detect from env keys",
)
@click.option("--api-key", default=None, help="Custom API key for the selected provider")
@click.option("--model", default=None, help="Custom model name for the selected provider")
@click.option("--publish", is_flag=True, help="Create GitHub release")
@click.option("--dry-run", is_flag=True, help="Generate output without creating tags or GitHub releases")
@click.option("--draft", is_flag=True, help="Publish GitHub release as draft")
@click.option("--prerelease", is_flag=True, help="Publish GitHub release as prerelease")
@click.option("--skip-tag", is_flag=True, help="Do not create or push a git tag before publishing")
@click.option("--github-repo", default=None, help="GitHub repo slug, e.g. owner/repo")
@click.option("--github-token", default=None, help="GitHub token. Default: GITHUB_TOKEN env var")
@click.option("--output", type=click.Path(), default=None, help="Write output to file")
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--notes-only", is_flag=True, help="Print only Suggested Release Notes")
@click.option("--ci-output", is_flag=True, help="Write version, bump_type, commit_count, release_url to GITHUB_OUTPUT")
@click.option("--mock-response", default=None, hidden=True, help="Read AI response from file for tests")
def main(
    from_ref,
    to_ref,
    version,
    provider,
    api_key,
    model,
    publish,
    dry_run,
    draft,
    prerelease,
    skip_tag,
    github_repo,
    github_token,
    output,
    output_format,
    notes_only,
    ci_output,
    mock_response,
):
    """Prepare, inspect, and optionally publish an AI-assisted release."""
    latest_tag = get_latest_tag()
    if not from_ref:
        from_ref = latest_tag
        if from_ref:
            click.echo(f"Using latest tag: {from_ref}", err=True)

    if not provider:
        if mock_response:
            provider = "mock"
        elif api_key:
            raise click.ClickException("Use --provider when passing --api-key.")
        else:
            try:
                provider = auto_detect_provider()
                click.echo(f"Using provider: {provider}", err=True)
            except EnvironmentError as exc:
                raise click.ClickException(str(exc))

    try:
        commits = get_commits(from_ref, to_ref)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() if exc.stderr else "Could not execute git log."
        raise click.ClickException(f"Git error: {detail}")

    if not commits:
        raise click.ClickException("No commits found in that range.")

    click.echo(f"Found {len(commits)} commits. Building release brief...", err=True)

    current_version = version or latest_tag or "v0.0.0"
    prompt = build_prompt(commits, current_version)

    try:
        ai_raw = call_provider(provider, prompt, api_key, model, mock_response)
    except Exception as exc:
        raise click.ClickException(f"Error calling {provider} provider: {exc}")

    bump_type, release_brief = parse_ai_response(ai_raw)
    if not version:
        version = bump_version(latest_tag, bump_type) if latest_tag else "v1.0.0"
        click.echo(f"Resolved release version: {version}", err=True)

    result = ReleaseResult(
        version=version,
        bump_type=bump_type,
        release_brief=release_brief,
        release_notes=extract_release_notes(release_brief),
        commit_count=len(commits),
        from_ref=from_ref,
        to_ref=to_ref,
        provider=provider,
    )

    if publish:
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token and not dry_run:
            raise click.ClickException("GitHub token not found. Set GITHUB_TOKEN or pass --github-token.")

        repo_slug = github_repo or get_github_repo_slug()
        if not repo_slug:
            raise click.ClickException("Could not detect GitHub repo. Pass --github-repo owner/repo.")

        if not skip_tag:
            try:
                create_and_push_tag(version, dry_run)
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.strip() if exc.stderr else "Tag create/push failed."
                raise click.ClickException(f"Git tag error: {detail}")

        result.published_url = publish_github_release(
            repo_slug=repo_slug,
            tag_name=version,
            name=f"Release {version}",
            body=result.release_notes if notes_only else build_output_document(result),
            token=token or "",
            draft=draft,
            prerelease=prerelease,
            dry_run=dry_run,
        )
        click.echo(f"Release URL: {result.published_url}", err=True)

    rendered = render_result(result, output_format, notes_only)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        click.echo(f"Saved output to {output}", err=True)
    else:
        click.echo(rendered)

    if ci_output:
        write_github_output(result)


if __name__ == "__main__":
    main()
