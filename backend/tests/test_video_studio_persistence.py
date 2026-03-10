import importlib.util
import json
from pathlib import Path

import pytest  # type: ignore


def _load_video_studio_module():
    module_path = Path(__file__).resolve().parents[1] / "skills" / "video-studio" / "scripts" / "run.py"
    if not module_path.exists():
        pytest.skip("video-studio run.py not present")
    spec = importlib.util.spec_from_file_location("video_studio_run_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_character_image_url_is_persisted_to_character_json(tmp_path):
    module = _load_video_studio_module()
    output_dir = tmp_path / "output" / "video_studio"
    pipeline = module.VideoStudioPipeline(str(output_dir), llm_client=None)

    char_file = output_dir / "characters" / "alice_prompt.json"
    char_file.parent.mkdir(parents=True, exist_ok=True)
    char_file.write_text(
        json.dumps(
            {
                "name": "Alice",
                "name_en": "Alice",
                "appearance": "red coat",
                "reference_prompt": "old prompt",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    production_plan = module.ProductionPlan(
        story="story",
        target_duration=30,
        style="cinematic",
        characters=[
            module.Character(
                name="Alice",
                description="hero",
                reference_path=str(char_file),
                reference_prompt="new prompt",
            )
        ],
        shots=[],
        total_estimated_duration=30,
    )

    updated = pipeline.apply_character_image_results(
        production_plan,
        [{"name": "Alice", "image_url": "https://example.com/alice.png"}],
    )

    assert updated == 1
    assert production_plan.characters[0].reference_image_url == "https://example.com/alice.png"

    persisted = json.loads(char_file.read_text(encoding="utf-8"))
    assert persisted["reference_image_url"] == "https://example.com/alice.png"
    assert persisted["reference_prompt"] == "new prompt"
    assert persisted["name_en"] == "Alice"


def test_storyboard_image_url_is_persisted_to_prompt_and_sequence_json(tmp_path):
    module = _load_video_studio_module()
    output_dir = tmp_path / "output" / "video_studio"
    pipeline = module.VideoStudioPipeline(str(output_dir), llm_client=None)

    shot_file = output_dir / "storyboard" / "shot_001_prompt.json"
    shot_file.parent.mkdir(parents=True, exist_ok=True)
    shot_file.write_text(
        json.dumps(
            {
                "shot_id": 1,
                "scene": "Opening",
                "image_prompt": "frame",
                "video_prompt": "pan",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    production_plan = module.ProductionPlan(
        story="story",
        target_duration=30,
        style="cinematic",
        characters=[],
        shots=[
            module.Shot(
                shot_id=1,
                prompt="pan",
                image_prompt="frame",
                duration=8.0,
                shot_type="wide",
                characters=[],
                scene_description="Opening",
                preview_image=str(shot_file),
            )
        ],
        total_estimated_duration=8.0,
    )

    updated = pipeline.apply_storyboard_image_results(
        production_plan,
        [{"shot_id": 1, "image_url": "https://example.com/shot-1.png"}],
    )

    assert updated == 1
    assert production_plan.shots[0].storyboard_image_url == "https://example.com/shot-1.png"

    persisted_shot = json.loads(shot_file.read_text(encoding="utf-8"))
    assert persisted_shot["storyboard_image_url"] == "https://example.com/shot-1.png"

    sequence_file = output_dir / "storyboard" / "storyboard_sequence.json"
    persisted_sequence = json.loads(sequence_file.read_text(encoding="utf-8"))
    assert persisted_sequence["shots"][0]["storyboard_image_url"] == "https://example.com/shot-1.png"



def test_storyboard_video_url_is_persisted_to_prompt_and_sequence_json(tmp_path):
    module = _load_video_studio_module()
    output_dir = tmp_path / "output" / "video_studio"
    pipeline = module.VideoStudioPipeline(str(output_dir), llm_client=None)

    shot_file = output_dir / "storyboard" / "shot_001_prompt.json"
    shot_file.parent.mkdir(parents=True, exist_ok=True)
    shot_file.write_text(
        json.dumps(
            {
                "shot_id": 1,
                "scene": "Opening",
                "image_prompt": "frame",
                "video_prompt": "pan",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    production_plan = module.ProductionPlan(
        story="story",
        target_duration=30,
        style="cinematic",
        characters=[],
        shots=[
            module.Shot(
                shot_id=1,
                prompt="pan",
                image_prompt="frame",
                duration=8.0,
                shot_type="wide",
                characters=[],
                scene_description="Opening",
                preview_image=str(shot_file),
            )
        ],
        total_estimated_duration=8.0,
    )

    updated = pipeline.apply_storyboard_video_results(
        production_plan,
        [{"shot_id": 1, "video_url": "https://example.com/shot-1.mp4"}],
    )

    assert updated == 1
    assert production_plan.shots[0].storyboard_video_url == "https://example.com/shot-1.mp4"
    assert production_plan.shots[0].video_url == "https://example.com/shot-1.mp4"

    persisted_shot = json.loads(shot_file.read_text(encoding="utf-8"))
    assert persisted_shot["storyboard_video_url"] == "https://example.com/shot-1.mp4"
    assert persisted_shot["video_url"] == "https://example.com/shot-1.mp4"

    sequence_file = output_dir / "storyboard" / "storyboard_sequence.json"
    persisted_sequence = json.loads(sequence_file.read_text(encoding="utf-8"))
    assert persisted_sequence["shots"][0]["storyboard_video_url"] == "https://example.com/shot-1.mp4"
    assert persisted_sequence["shots"][0]["video_url"] == "https://example.com/shot-1.mp4"
