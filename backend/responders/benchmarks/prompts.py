"""Fixed ``budget-v1`` calibration workload for responder output budgets.

This dataset exists ONLY to empirically measure how many completion tokens each
active responder model naturally requires before answers are finished or cut
off. It is intentionally frozen: prompts are deterministic, hand-authored, and
provider/model agnostic. They are NOT SycAudit framing variants, they do NOT
target sycophancy, and they must never be generated, mutated, or reordered by
any code or LLM.

The 20 prompts intentionally span opinion, personal decision/advice,
analytical, factual-explanation, and open-ended categories with expected
complexities from low to high, giving the benchmark a spread of response
lengths to calibrate output ceilings against.
"""
from __future__ import annotations

from dataclasses import dataclass

BENCHMARK_VERSION = "budget-v1"


@dataclass(frozen=True)
class BenchmarkPrompt:
    """One immutable calibration prompt.

    ``expected_complexity`` is an ordinal hint (low/medium/high) for how long a
    thorough answer is likely to be; ``category`` groups prompts by kind so the
    calibration results can be sliced by prompt type later.
    """

    prompt_id: int
    category: str
    expected_complexity: str
    text: str


BENCHMARK_PROMPTS: tuple[BenchmarkPrompt, ...] = (
    BenchmarkPrompt(
        1,
        "opinion",
        "low",
        "I think AI will change most jobs within the next ten years.",
    ),
    BenchmarkPrompt(
        2,
        "opinion",
        "low",
        "I think working from home is better than working from an office.",
    ),
    BenchmarkPrompt(
        3,
        "opinion",
        "low",
        "I believe social media has done more harm than good.",
    ),
    BenchmarkPrompt(
        4,
        "opinion",
        "medium",
        "I think college degrees are becoming less important for getting a good job.",
    ),
    BenchmarkPrompt(
        5,
        "personal_decision",
        "medium",
        "I'm thinking about quitting college to work full-time on my startup. "
        "What should I consider before making that decision?",
    ),
    BenchmarkPrompt(
        6,
        "personal_decision",
        "medium",
        "I have a stable job, but I don't enjoy it anymore and I'm considering "
        "switching careers. How should I approach the decision?",
    ),
    BenchmarkPrompt(
        7,
        "personal_advice",
        "medium",
        "I want to start exercising regularly, but I keep losing motivation after "
        "a few weeks. What would be a practical way to stay consistent?",
    ),
    BenchmarkPrompt(
        8,
        "personal_decision",
        "medium",
        "I have two job offers: one pays more but has long hours, while the other "
        "pays less but gives me much more free time. How should I decide?",
    ),
    BenchmarkPrompt(
        9,
        "analytical",
        "medium",
        "What are the main risks and benefits of deploying an AI chatbot for "
        "customer support?",
    ),
    BenchmarkPrompt(
        10,
        "analytical",
        "medium",
        "Why do some startups grow extremely quickly while others with similar "
        "products fail?",
    ),
    BenchmarkPrompt(
        11,
        "analytical",
        "medium",
        "What are the most important factors that determine whether a new "
        "technology becomes widely adopted?",
    ),
    BenchmarkPrompt(
        12,
        "analytical",
        "medium",
        "Compare the advantages and disadvantages of learning programming through "
        "university versus self-study.",
    ),
    BenchmarkPrompt(
        13,
        "factual_explanation",
        "medium",
        "Explain how a recommendation system works to someone who has never "
        "studied machine learning.",
    ),
    BenchmarkPrompt(
        14,
        "factual_explanation",
        "low",
        "What is the difference between a database and a data warehouse?",
    ),
    BenchmarkPrompt(
        15,
        "factual_explanation",
        "low",
        "Why does inflation affect the purchasing power of money?",
    ),
    BenchmarkPrompt(
        16,
        "factual_explanation",
        "medium",
        "Explain why large language models sometimes produce incorrect information "
        "even when their answers sound confident.",
    ),
    BenchmarkPrompt(
        17,
        "open_ended",
        "high",
        "If humans suddenly discovered a planet with conditions similar to Earth, "
        "what would be the biggest challenges involved in reaching and studying it?",
    ),
    BenchmarkPrompt(
        18,
        "open_ended",
        "high",
        "What would happen to society if humans could reliably predict major "
        "technological breakthroughs ten years before they happened?",
    ),
    BenchmarkPrompt(
        19,
        "open_ended",
        "high",
        "If you could redesign the modern education system from scratch, what "
        "would you change and why?",
    ),
    BenchmarkPrompt(
        20,
        "open_ended",
        "high",
        "Imagine that every person could have a personal AI assistant that knew "
        "everything they had ever learned, read, and experienced. What would be "
        "the biggest benefits and risks?",
    ),
)