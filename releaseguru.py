#!/usr/bin/env python3
import os
import re
import subprocess
import click
import requests
from dotenv import load_dotenv
from providers import PROVIDERS, auto_detect_provider

load_dotenv()  # loads .env file automatically

def get_commits(from_ref: str | None, to_ref: str) -> list[str]:
    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
    result = subprocess.run(
        ["git", "log", range_spec, "--pretty=format:%s (%an)"],
        capture_output=True, text=True, check=True
    )
    return [l.strip() for l in result.stdout.splitlines() if l.strip()]

def get_latest_tag() -> str | None:
    r = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True
    )
    return r.stdout.strip() if r.returncode == 0 else None

def get_github_repo_slug() -> str | None:
    """Extract owner/repo from the git remote origin URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True
        )
        url = result.stdout.strip()
        # Matches https://github.com/owner/repo.git or git@github.com:owner/repo.git
        match = re.search(r"github\.com[:/]([^/]+)/([^.]+)(?:\.git)?", url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    except Exception:
        pass
    return None

def bump_version(version: str, bump_type: str) -> str:
    """Safely bumps a version string (e.g. v1.2.3 or 1.2.3) based on SemVer bump type."""
    # Find the version digits
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        # Fallback if version string is not standard SemVer
        return f"{version}-{bump_type}-bump"
    
    major, minor, patch = map(int, match.groups())
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
        
    # Preserve leading 'v' if it was present
    prefix = "v" if version.lower().startswith("v") else ""
    return f"{prefix}{major}.{minor}.{patch}"

def build_prompt(commits: list[str], version_label: str) -> str:
    lines = "\n".join(f"- {c}" for c in commits)
    return f"""You are a technical writer and release manager. Analyze these git commits and convert them into a clean, user-facing changelog.

In your response, you MUST first include a recommended semantic version bump. Choose exactly one of: major, minor, or patch.
Follow the standard SemVer rules:
- Choose 'major' if there are breaking changes.
- Choose 'minor' if new features are added.
- Choose 'patch' if there are only bug fixes, chores, or documentation updates.

Format the very first line of your output EXACTLY like this:
__RECOMMENDED_BUMP__: <bump_type>

Followed by the changelog content. Group the commits into these sections (skip empty ones):
## Features
## Bug Fixes
## Breaking Changes
## Improvements

Rules:
- Present tense: "Add login" not "Added login"
- User-facing language — no internal jargon
- Skip chore/ci/lint commits unless important
- One sentence max per item

Commits:
{lines}

Output only the `__RECOMMENDED_BUMP__` line and the Markdown. No preamble, no explanation."""

def publish_github_release(repo_slug: str, tag_name: str, name: str, body: str, token: str):
    """Creates a new release on GitHub using the API."""
    url = f"https://api.github.com/repos/{repo_slug}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code not in (200, 201):
        raise Exception(f"GitHub API Error: {resp.status_code} - {resp.text}")
    return resp.json().get("html_url")

@click.command()
@click.option("--from", "from_ref", default=None,
              help="Start tag/ref. Default: latest git tag")
@click.option("--to", "to_ref", default="HEAD",
              help="End ref. Default: HEAD")
@click.option("--version", default=None,
              help="Explicit version label. Default: auto-bumps latest tag using AI recommendation")
@click.option("--provider", default=None,
              type=click.Choice(["groq","openai","anthropic","gemini","xai"]),
              help="LLM provider. Default: auto-detect from env keys")
@click.option("--api-key", default=None,
              help="Provide your own custom API key for the selected provider.")
@click.option("--model", default=None,
              help="Provide your own custom model name to use for the selected provider.")
@click.option("--publish", is_flag=True,
              help="Automatically publish the release to GitHub.")
@click.option("--github-token", default=None,
              help="GitHub Personal Access Token for publishing. Default: GITHUB_TOKEN env var")
@click.option("--output", type=click.Path(), default=None,
              help="Write output to this file instead of stdout")
def main(from_ref, to_ref, version, provider, api_key, model, publish, github_token, output):
    """Generate a changelog from git commits using AI with SemVer advice & one-click publishing.

    Requires one of: GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY,
    ANTHROPIC_API_KEY, or XAI_API_KEY in your environment or .env file.
    """
    # Auto-detect missing refs
    latest_tag = get_latest_tag()
    if not from_ref:
        from_ref = latest_tag
        if from_ref:
            click.echo(f"Using latest tag: {from_ref}", err=True)

    # Auto-detect provider if not explicitly given
    if not provider:
        if api_key:
            raise click.ClickException(
                "You must specify --provider when using a custom --api-key."
            )
        try:
            provider = auto_detect_provider()
            click.echo(f"Using provider: {provider}", err=True)
        except EnvironmentError as e:
            raise click.ClickException(str(e))

    # Fetch commits
    try:
        commits = get_commits(from_ref, to_ref)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Git error: {e.stderr.strip() if e.stderr else 'Could not execute git log.'}")

    if not commits:
        raise click.ClickException("No commits found in that range.")

    click.echo(f"Found {len(commits)} commits — generating...", err=True)

    # Call the selected provider with prompt
    try:
        ai_raw = PROVIDERS[provider](build_prompt(commits, version or "next"), api_key=api_key, model=model)
    except Exception as e:
        raise click.ClickException(f"Error calling {provider} provider: {e}")

    # Parse recommended bump and changelog text
    bump_type = "patch"  # fallback
    changelog_lines = []
    
    for line in ai_raw.splitlines():
        if line.startswith("__RECOMMENDED_BUMP__"):
            match = re.search(r"__RECOMMENDED_BUMP__:\s*(\w+)", line)
            if match:
                bump_type = match.group(1).lower().strip()
        else:
            changelog_lines.append(line)
            
    changelog_text = "\n".join(changelog_lines).strip()
    
    # Calculate the final version label
    if not version:
        if latest_tag:
            version = bump_version(latest_tag, bump_type)
            click.echo(f"AI recommended bump ({bump_type}): {latest_tag} ➡️ {version}", err=True)
        else:
            version = "v1.0.0"
            click.echo(f"No tag found. Defaulting to first release version: {version}", err=True)

    # Output changelog
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(changelog_text)
        click.echo(f"Saved changelog to {output}", err=True)
    else:
        # Prepend version header to stdout for clean visibility
        click.echo(f"# Release Notes {version}\n")
        click.echo(changelog_text)

    # Handle GitHub publishing
    if publish:
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise click.ClickException(
                "GitHub Token not found. Provide it via GITHUB_TOKEN in your .env or --github-token."
            )
            
        repo_slug = get_github_repo_slug()
        if not repo_slug:
            raise click.ClickException(
                "Could not auto-detect GitHub repository from remote URL. Please verify git origin is set."
            )
            
        click.echo(f"Auto-detected repository: {repo_slug}", err=True)
        click.echo(f"Publishing release '{version}' to GitHub...", err=True)
        
        try:
            # We can create a local tag if git commands are available
            subprocess.run(["git", "tag", "-a", version, "-m", f"Release {version}"], capture_output=True)
            # Try to push local tag
            subprocess.run(["git", "push", "origin", version], capture_output=True)
        except Exception:
            pass  # Fail gracefully, GitHub API can auto-create the tag from branch/ref
            
        try:
            release_url = publish_github_release(
                repo_slug=repo_slug,
                tag_name=version,
                name=f"Release {version}",
                body=changelog_text,
                token=token
            )
            click.echo(f"Successfully published! View release at: {release_url}", err=True)
        except Exception as e:
            raise click.ClickException(f"Failed to publish to GitHub: {e}")

if __name__ == "__main__":
    main()
