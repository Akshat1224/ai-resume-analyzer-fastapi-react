import pytest
import anyio
from app.services.interview_service import generate_interview_questions


def test_offline_generator_respects_num_questions():
    """Offline heuristic generator should return exactly the requested number of questions."""
    async def _test():
        result = await generate_interview_questions(
            role="Software Engineer",
            industry="Technology",
            experience_level="Mid",
            difficulty="medium",
            num_questions=7,
            skill_gaps=None,
            session_id="test_num_questions",
        )

        assert "questions" in result
        assert len(result["questions"]) == 7, f"Expected 7 questions, got {len(result['questions'])}"

    anyio.run(_test)


def test_offline_generator_with_skill_gaps_respects_num_questions():
    """Offline generator with skill gaps should return exactly the requested number of questions."""
    async def _test():
        result = await generate_interview_questions(
            role="DevOps Engineer",
            industry="Fintech",
            experience_level="Senior",
            difficulty="hard",
            num_questions=5,
            skill_gaps=["Kubernetes", "Docker"],
            session_id="test_num_questions_gaps",
        )

        assert "questions" in result
        assert len(result["questions"]) == 5, f"Expected 5 questions, got {len(result['questions'])}"

    anyio.run(_test)
