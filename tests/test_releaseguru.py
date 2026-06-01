import json
import unittest

from releaseguru import (
    __version__,
)
from releaseguru.cli import ReleaseResult, bump_version, extract_release_notes, parse_ai_response, render_result


class ReleaseGuruTests(unittest.TestCase):
    def test_version_exists(self):
        self.assertEqual(__version__, "0.1.0")

    def test_bump_version(self):
        self.assertEqual(bump_version("v1.2.3", "major"), "v2.0.0")
        self.assertEqual(bump_version("v1.2.3", "minor"), "v1.3.0")
        self.assertEqual(bump_version("v1.2.3", "patch"), "v1.2.4")

    def test_parse_ai_response(self):
        bump, body = parse_ai_response("__RECOMMENDED_BUMP__: minor\n# Release Assistant Brief")

        self.assertEqual(bump, "minor")
        self.assertEqual(body, "# Release Assistant Brief")

    def test_extract_release_notes(self):
        notes = extract_release_notes(
            "# Release Assistant Brief\n"
            "## Release Summary\n"
            "Text\n"
            "## Suggested Release Notes\n"
            "### Features\n"
            "- Add export"
        )

        self.assertEqual(notes, "### Features\n- Add export")

    def test_render_json(self):
        result = ReleaseResult(
            version="v1.0.0",
            bump_type="minor",
            release_brief="# Brief",
            release_notes="### Features\n- Add export",
            commit_count=2,
            from_ref="v0.9.0",
            to_ref="HEAD",
            provider="mock",
        )

        rendered = render_result(result, "json", notes_only=False)
        payload = json.loads(rendered)

        self.assertEqual(payload["version"], "v1.0.0")
        self.assertEqual(payload["bump_type"], "minor")
        self.assertEqual(payload["commit_count"], 2)


if __name__ == "__main__":
    unittest.main()
