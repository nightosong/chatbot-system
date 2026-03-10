import asyncio
import importlib.util
from pathlib import Path

import pytest  # type: ignore


def _load_video_studio_module():
    module_path = Path(__file__).resolve().parents[1] / "skills" / "video-studio" / "scripts" / "run.py"
    if not module_path.exists():
        pytest.skip("video-studio run.py not present")
    spec = importlib.util.spec_from_file_location("video_studio_run_brief_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_story_requires_explicit_style_and_duration(monkeypatch):
    module = _load_video_studio_module()
    monkeypatch.setattr(module.SkillLLMClient, "from_context", staticmethod(lambda context: object()))

    result = asyncio.run(
        module.run(
            {
                "action": "analyze_story",
                "story": "A turtle races a rabbit.",
            },
            context={},
        )
    )

    assert result["success"] is False
    assert result["action"] == "analyze_story"
    assert "video style and target duration" in result["error"]


def test_constrain_shot_plan_limits_count_and_rebalances_duration():
    module = _load_video_studio_module()
    raw_shots = [
        {"shot_id": idx + 1, "scene_description": f"scene-{idx + 1}", "duration": 8.0}
        for idx in range(8)
    ]

    constrained = module._constrain_shot_plan(raw_shots, 30)
    guidance = module._shot_count_guidance(30)

    assert len(constrained) == guidance["max"]
    assert [shot["shot_id"] for shot in constrained] == [1, 2, 3, 4, 5]
    assert round(sum(shot["duration"] for shot in constrained), 1) == 30.0




def test_style_preset_alias_and_fields():
    module = _load_video_studio_module()
    preset = module._style_preset("pixar")

    assert module._normalize_style("pixar") == "3d animation"
    assert preset["label"] == "3D Animation"
    assert "family-film" in preset["style_direction"]
    assert "friendly proportions" in preset["character_direction"]
    assert "readability-first" in preset["storyboard_direction"]

def test_generate_storyboard_uses_style_and_saved_shot_metadata(monkeypatch, tmp_path):
    module = _load_video_studio_module()
    captured = {}

    def fake_build_shot_prompts(client, scene, shot_type, camera_movement, characters, char_appearances, mood, time_of_day, location, style):
        captured.update(
            {
                "scene": scene,
                "shot_type": shot_type,
                "camera_movement": camera_movement,
                "characters": characters,
                "char_appearances": char_appearances,
                "mood": mood,
                "time_of_day": time_of_day,
                "location": location,
                "style": style,
            }
        )
        return {"video_prompt": "video prompt", "image_prompt": "image prompt"}

    monkeypatch.setattr(module, "_llm_build_shot_prompts", fake_build_shot_prompts)

    output_dir = tmp_path / "output" / "video_studio"
    pipeline = module.VideoStudioPipeline(str(output_dir), llm_client=object())
    production_plan = module.ProductionPlan(
        story="story",
        target_duration=30,
        style="anime",
        characters=[
            module.Character(
                name="Rabbit",
                description="fast rabbit",
                appearance="white rabbit with red scarf",
                personality="playful and proud",
            )
        ],
        shots=[
            module.Shot(
                shot_id=1,
                prompt="old video",
                duration=8.0,
                shot_type="close-up",
                characters=["Rabbit"],
                scene_description="Rabbit looks back confidently",
                camera_movement="dolly in",
                mood="competitive",
                time_of_day="morning",
                location="forest trail",
                style="anime",
            )
        ],
        total_estimated_duration=8.0,
    )

    result = asyncio.run(pipeline.generate_storyboard_previews(production_plan))

    assert result["generated"][0]["prompt"] == "video prompt"
    assert captured["style"] == "anime"
    assert captured["camera_movement"] == "dolly in"
    assert captured["mood"] == "competitive"
    assert captured["time_of_day"] == "morning"
    assert captured["location"] == "forest trail"
    assert captured["char_appearances"]["Rabbit"] == "white rabbit with red scarf"
