from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIRTUAL_PRODUCTION_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "virtual-production" / "scripts"
)
sys.path.insert(0, str(VIRTUAL_PRODUCTION_SCRIPTS))

from generation.requests import _runtime_reference_media_content  # noqa: E402


class RuntimeReferenceUploadTests(unittest.TestCase):
    def test_provider_last_frame_is_reuploaded_before_successor_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            task_dir = Path(temporary_directory)
            source_dir = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / "segment-002"
            )
            source_dir.mkdir(parents=True)
            source = source_dir / "last-frame.png"
            source.write_bytes(b"accepted-last-frame")
            (source_dir / "production-record.json").write_text(
                json.dumps(
                    {
                        "status": "PICTURE_GENERATED",
                        "provider_attempt_id": "segment-002__attempt-0001",
                        "last_frame_source_url": (
                            "https://provider-output.tos.example/expired.png"
                        ),
                    }
                ),
                encoding="utf-8",
            )
            segment = {
                "generation_task_id": "segment-003",
                "runtime_media": [
                    {
                        "provider_token": "@Image5",
                        "source_kind": "provider_last_frame",
                        "source_segment_id": "segment-002",
                        "source_provider_attempt_id": "segment-002__attempt-0001",
                    }
                ],
            }

            with patch(
                "generation.requests.provider_runtime.tos_upload_path",
                return_value={
                    "public_url": "https://project-storage.example/last-frame.png"
                },
            ) as upload:
                content = _runtime_reference_media_content(
                    segment,
                    task_dir=task_dir,
                )

            upload.assert_called_once_with(
                source,
                kind="inputs/provider-last-frame",
            )
            self.assertEqual(
                content[0]["image_url"]["url"],
                "https://project-storage.example/last-frame.png",
            )

    def test_complete_predecessor_uses_seedance_source_before_dubbing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            task_dir = Path(temporary_directory)
            source_dir = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / "segment-002"
            )
            source_dir.mkdir(parents=True)
            seedance_source = source_dir / "seedance-source.mp4"
            seedance_source.write_bytes(b"immutable Seedance source")
            (source_dir / "production-record.json").write_text(
                json.dumps(
                    {
                        "status": "PICTURE_GENERATED",
                        "provider_attempt_id": "segment-002__attempt-0001",
                    }
                ),
                encoding="utf-8",
            )
            segment = {
                "generation_task_id": "segment-003",
                "runtime_media": [
                    {
                        "provider_token": "@Video1",
                        "source_kind": "complete_predecessor_video",
                        "source_segment_id": "segment-002",
                        "source_provider_attempt_id": "segment-002__attempt-0001",
                    }
                ],
            }

            with patch(
                "generation.requests.provider_runtime.tos_upload_path",
                return_value={
                    "public_url": "https://project-storage.example/source.mp4"
                },
            ) as upload:
                content = _runtime_reference_media_content(
                    segment,
                    task_dir=task_dir,
                )

            upload.assert_called_once_with(
                seedance_source,
                kind="inputs/complete-predecessor-video",
            )
            self.assertEqual(
                content[0]["video_url"]["url"],
                "https://project-storage.example/source.mp4",
            )


if __name__ == "__main__":
    unittest.main()
