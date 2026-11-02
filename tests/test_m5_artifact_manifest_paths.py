"""Path rendering checks for the private M5 artifact manifest CLI."""

from pathlib import Path
import unittest

from scripts.m5_artifact_manifests import display_artifact_path


class ArtifactManifestPathTests(unittest.TestCase):
    def test_repository_artifact_path_is_relative(self) -> None:
        repository = Path("/tmp/example-repository")
        artifact = repository / "artifacts/m5/artifact-manifest.json"
        self.assertEqual(
            display_artifact_path(artifact, repository),
            "artifacts/m5/artifact-manifest.json",
        )

    def test_external_artifact_store_is_reported_as_absolute_path(self) -> None:
        repository = Path("/tmp/example-repository")
        artifact = Path("/tmp/private-model-store/artifacts/m5/artifact-manifest.json")
        self.assertEqual(display_artifact_path(artifact, repository), artifact.as_posix())


if __name__ == "__main__":
    unittest.main()
