import time
import re
from typing import Dict, Any, List, Optional

from app.services.ai_service import analyze_resume, get_groq_api_key
from app.services.prompt_service import build_interview_questions_prompt
from app.services.cache_service import cache_service
from app.services.history_service import (
    save_practice_attempt,
    get_skill_progress,
    get_adaptive_difficulty_for_skill,
)
from app.schemas.interview_schema import (
    PracticeAttemptRequest,
    PracticeAttemptResponse,
    ProgressSummaryResponse,
    SkillProgress,
)
from app.core.telemetry import logger


def build_gap_targeted_interview_prompt(
    role: str,
    industry: str,
    experience_level: str,
    difficulty: str,
    skill_gaps: List[str],
    num_questions: int = 5,
) -> str:
    """Prompt tailored specifically to evaluate identified candidate skill gaps."""
    gaps_str = ", ".join(skill_gaps[:5])
    return f"""Generate {num_questions} technical interview questions for a {experience_level} {role} in {industry}.
Difficulty: {difficulty}.
CRITICAL FOCUS: The candidate has demonstrated skill gaps in: {gaps_str}.
Design practical, scenario-based interview questions specifically testing understanding of these areas.

Reply with ONLY a JSON object in this exact format:
{{
  "questions": [
    {{
      "question": "...",
      "hints": "...",
      "sample_answer": "...",
      "difficulty": "{difficulty}",
      "target_skill": "<one of the targeted skill gaps>"
    }}
  ]
}}

Rules:
- sample_answer must be plain text
- hints must be concise
- question must directly evaluate one of the targeted skill gaps"""


async def generate_interview_questions(
    role: str,
    industry: str,
    experience_level: str,
    difficulty: str,
    num_questions: int = 5,
    skill_gaps: Optional[List[str]] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Generates interview questions with adaptive difficulty targeting identified skill gaps
    and deterministic tiered caching.
    """
    # 1. Adapt difficulty if specific skill gaps provided
    effective_difficulty = difficulty
    if skill_gaps:
        primary_gap = skill_gaps[0]
        effective_difficulty = get_adaptive_difficulty_for_skill(session_id, primary_gap, difficulty)

    cache_key = (
        cache_service.build_interview_cache_key(
            role=role,
            industry=industry,
            experience_level=experience_level,
            difficulty=effective_difficulty,
            num_questions=num_questions,
        )
        + (f":gaps_{'_'.join(sorted(skill_gaps[:3]))}" if skill_gaps else "")
    )

    # 2. Check cache
    cached_data = await cache_service.get(cache_key)
    if cached_data:
        logger.info(f"[CACHE HIT] Interview questions for role='{role}', count={num_questions}")
        return cached_data

    # 3. Build prompt
    if skill_gaps:
        prompt = build_gap_targeted_interview_prompt(
            role, industry, experience_level, effective_difficulty, skill_gaps, num_questions
        )
    else:
        prompt = build_interview_questions_prompt(
            role, industry, experience_level, effective_difficulty, num_questions
        )

    # 4. Generate
    start = time.perf_counter()
    api_key = get_groq_api_key()

    if api_key:
        result = await analyze_resume(prompt, max_tokens=1200)
    else:
        # Offline heuristic question generator - respect num_questions
        base_questions = [
            {
                "question": f"How do you approach designing scalable systems in {role} within the {industry} domain?",
                "hints": "Discuss architectural patterns, throughput, and error boundaries.",
                "sample_answer": f"In {industry}, I prioritize high availability, modular decoupling, and robust observability.",
                "difficulty": effective_difficulty,
                "target_skill": skill_gaps[0] if skill_gaps else role,
            },
            {
                "question": f"When addressing {skill_gaps[0] if skill_gaps else 'production incidents'}, what debugging strategy do you follow?",
                "hints": "Mention logging, tracing, reproduction steps, and root-cause analysis.",
                "sample_answer": "I examine distributed traces, verify metrics spikes, isolate the regression, and draft an RCA.",
                "difficulty": effective_difficulty,
                "target_skill": skill_gaps[0] if skill_gaps else "System Design",
            },
        ]
        # Generate requested number of questions by cycling through base templates
        questions = []
        for i in range(num_questions):
            base_q = base_questions[i % len(base_questions)]
            questions.append({
                **base_q,
                "question": f"{base_q['question']} (Variation {i + 1})" if i >= len(base_questions) else base_q["question"],
            })
        result = {"questions": questions}

    elapsed = time.perf_counter() - start
    logger.info(f"[INTERVIEW GENERATOR] Generation completed in {elapsed:.2f}s")

    # Validate and ensure correct number of questions
    if isinstance(result, dict) and "error" not in result:
        questions = result.get("questions", [])
        if not isinstance(questions, list):
            questions = []

        # If LLM returned fewer questions than requested, regenerate missing ones
        if len(questions) < num_questions:
            logger.warning(f"[INTERVIEW GENERATOR] LLM returned {len(questions)} questions, requested {num_questions}. Regenerating missing.")
            missing_count = num_questions - len(questions)
            for i in range(missing_count):
                questions.append({
                    "question": f"Describe a challenging {role} scenario in {industry} you've encountered and how you resolved it.",
                    "hints": "Focus on problem identification, solution approach, and outcome measurement.",
                    "sample_answer": "I identified the bottleneck through metrics analysis, implemented a caching layer, and reduced latency by 40%.",
                    "difficulty": effective_difficulty,
                    "target_skill": skill_gaps[i % len(skill_gaps)] if skill_gaps else role,
                })

        result["questions"] = questions[:num_questions]  # Ensure exactly num_questions
        result["session_id"] = session_id
        result["adapted_from_gaps"] = bool(skill_gaps)
        await cache_service.set(cache_key, result, ttl=3600)

    return result


async def evaluate_practice_attempt(payload: PracticeAttemptRequest) -> PracticeAttemptResponse:
    """
    Evaluates a candidate's answer to an interview question, records progress in SQLite,
    and calculates adaptive difficulty for subsequent questions.
    """
    answer_text = payload.user_answer.strip()
    words = answer_text.split()
    word_count = len(words)

    # Objective heuristic grading (or LLM if available)
    score = 0
    feedback_points = []
    suggestions = []

    # 1. Depth & Length (max 40 pts)
    if word_count >= 50:
        score += 40
        feedback_points.append("Comprehensive, detailed answer structure.")
    elif word_count >= 25:
        score += 25
        feedback_points.append("Good initial answer, but could expand on edge cases.")
        suggestions.append("Provide more technical detail and specific implementation context.")
    else:
        score += 15
        feedback_points.append("Brief answer; lacked depth.")
        suggestions.append("Structure answers using STAR method (Situation, Task, Action, Result).")

    # 2. Technical Vocabulary & Keyword presence (max 35 pts)
    skill_words = [w.lower() for w in payload.target_skill.split() if len(w) > 2]
    has_skill_mention = any(w in answer_text.lower() for w in skill_words)
    if has_skill_mention:
        score += 20
        feedback_points.append(f"Directly addressed core concepts related to {payload.target_skill}.")
    else:
        suggestions.append(f"Explicitly mention how you applied {payload.target_skill}.")

    technical_terms = ["architecture", "scale", "performance", "tradeoff", "latency", "testing", "monitoring", "error", "security"]
    found_terms = sum(1 for t in technical_terms if t in answer_text.lower())
    if found_terms >= 2:
        score += 15
        feedback_points.append("Demonstrated good engineering breadth and trade-off awareness.")
    elif found_terms >= 1:
        score += 8

    # 3. Clarity & Professional Tone (max 25 pts)
    if not re.search(r"\b(idk|dunno|maybe|guess)\b", answer_text.lower()):
        score += 25
    else:
        score += 10
        suggestions.append("Speak with confidence; avoid hesitant phrases like 'I guess'.")

    score = max(10, min(100, score))

    # Adaptive difficulty progression
    if score >= 85:
        next_diff = "hard"
    elif score >= 60:
        next_diff = "medium"
    else:
        next_diff = "easy"

    full_feedback = " ".join(feedback_points)

    # Persist attempt to SQLite history
    attempt_id = save_practice_attempt(
        session_id=payload.session_id or "default",
        target_skill=payload.target_skill,
        difficulty=payload.difficulty,
        question=payload.question,
        user_answer=payload.user_answer,
        feedback=full_feedback,
        score=score,
    )

    return PracticeAttemptResponse(
        attempt_id=attempt_id,
        target_skill=payload.target_skill,
        score=score,
        feedback=full_feedback,
        suggested_improvements=suggestions,
        next_difficulty=next_diff,
    )


def fetch_progress_summary(session_id: str = "default") -> ProgressSummaryResponse:
    raw_progress = get_skill_progress(session_id)
    skills_list = [SkillProgress(**item) for item in raw_progress]

    recommended = [
        s.skill for s in skills_list if s.mastery_status == "needs_practice"
    ]

    total_attempts = sum(s.attempts_count for s in skills_list)

    return ProgressSummaryResponse(
        session_id=session_id,
        total_attempts=total_attempts,
        skills_tracked=skills_list,
        recommended_focus=recommended,
    )