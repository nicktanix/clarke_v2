"""Memory significance classification — separate signal from noise.

Classifies interactions by type and assigns a significance score that determines
whether and how prominently a memory should be stored and retrieved.

Memory types:
  - bug_fix:       Error/bug reported and resolved — stores fix AND prevention guidance
  - code_pattern:  Style guide, convention, or pattern established
  - correction:    User corrected a response
  - decision:      Architectural or technical decision made
  - preference:    User stated a preference or instruction
  - conceptual:    Design/architecture discussion
  - factual:       Specific numbers, configs, versions
  - conversational: Standard substantive Q&A
  - noise:         Greetings, acknowledgments, trivial
"""

import re

from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)

# --- High-significance: coding context ---

_BUG_FIX_PATTERNS = re.compile(
    r"("
    # Error indicators in user message (pasted errors)
    r"traceback|stacktrace|stack trace|exception|error:|stderr|"
    r"failed with|crash|segfault|core dump|panic|fatal|"
    r"TypeError|ValueError|KeyError|AttributeError|ImportError|RuntimeError|"
    r"SyntaxError|NameError|IndexError|ModuleNotFoundError|"
    r"NullPointerException|NoSuchElementException|"
    r"ECONNREFUSED|ETIMEDOUT|ENOENT|EPERM|ENOMEM|"
    r"HTTP [45]\d\d|status.code.[45]\d\d|"
    r"cannot read propert|undefined is not|null reference|"
    # Fix indicators in answer
    r"the fix is|fixed by|root cause|the issue was|the problem was|"
    r"to fix this|the bug was|this error occurs when|"
    r"workaround|hotfix|patch"
    r")",
    re.IGNORECASE,
)

_CODE_PATTERN_PATTERNS = re.compile(
    r"\b("
    # Style and convention
    r"style guide|coding standard|naming convention|code review|"
    r"best practice|anti.?pattern|code smell|refactor|"
    r"don't use .+ use .+ instead|prefer .+ over|always use|never use|"
    # Patterns and architecture
    r"design pattern|factory pattern|singleton|observer|"
    r"repository pattern|dependency injection|middleware|decorator|"
    # Code quality
    r"linting|type hint|docstring|type annotation|"
    r"test coverage|unit test|integration test|"
    r"pre.?commit|CI.?CD|lint rule|"
    # Security patterns
    r"SQL injection|XSS|CSRF|input validation|sanitiz|escap"
    r")\b",
    re.IGNORECASE,
)

_PREVENTION_PATTERNS = re.compile(
    r"\b("
    r"to prevent|to avoid|in the future|going forward|"
    r"make sure to|always check|never forget|watch out for|"
    r"common mistake|common pitfall|lesson learned|"
    r"should have|could have avoided|next time"
    r")\b",
    re.IGNORECASE,
)

# --- High-significance: decisions and preferences ---

_DECISION_PATTERNS = re.compile(
    r"\b(decided|chosen|selected|adopted|rejected|approved|deprecated|switched to|migrated to|"
    r"we will use|we should use|from now on|the plan is|agreed to)\b",
    re.IGNORECASE,
)

_PREFERENCE_PATTERNS = re.compile(
    r"\b(i prefer|i like|i want|i need|please always|please never|don't ever|"
    r"make sure to|remember that|important:|note:)\b",
    re.IGNORECASE,
)

_CORRECTION_PATTERNS = re.compile(
    r"\b(actually|correction|that's wrong|that's not right|no,|incorrect|"
    r"the correct answer|should be|instead of|not .+ but)\b",
    re.IGNORECASE,
)

# --- Moderate-significance ---

_FACTUAL_PATTERNS = re.compile(
    r"\b(version \d|port \d|timeout.{1,30}\d|limit.{1,30}\d|"
    r"maximum.{1,30}\d|default.{1,30}\d|configured.{1,30}to|"
    r"is \d[\d,.]+|set to \d|equals \d|pool size.{1,20}\d)\b",
    re.IGNORECASE,
)

# --- Low-significance ---

_NOISE_PATTERNS = re.compile(
    r"\b(hello|hi there|thanks|thank you|ok|okay|got it|sure|yes|no|"
    r"bye|goodbye|how are you|what's up)\b",
    re.IGNORECASE,
)


class MemorySignificance:
    """Classification result for an interaction's memory significance."""

    def __init__(
        self,
        score: float,
        memory_type: str,
        should_store: bool,
        reason: str,
    ) -> None:
        self.score = score  # 0.0 (noise) to 1.0 (critical)
        self.memory_type = memory_type
        self.should_store = should_store
        self.reason = reason


def classify_significance(
    message: str,
    answer: str,
    query_features: dict | None = None,
) -> MemorySignificance:
    """Classify the significance of a query-answer interaction.

    Returns a MemorySignificance with score, type, and storage recommendation.
    """
    combined = f"{message} {answer}"
    features = query_features or {}

    # --- Highest priority: user corrections ---

    if _CORRECTION_PATTERNS.search(message):
        return MemorySignificance(
            score=0.85,
            memory_type="correction",
            should_store=True,
            reason="User corrected a response",
        )

    # --- Bug fixes: error pasted + fix provided ---
    # Check if the user pasted an error AND the answer contains a fix
    msg_has_error = _BUG_FIX_PATTERNS.search(message)
    answer_has_fix = _BUG_FIX_PATTERNS.search(answer)

    if msg_has_error and answer_has_fix:
        # Both error and fix present — high-value bug fix memory
        has_prevention = _PREVENTION_PATTERNS.search(combined)
        return MemorySignificance(
            score=0.95 if has_prevention else 0.9,
            memory_type="bug_fix",
            should_store=True,
            reason="Bug reported and fixed"
            + (" with prevention guidance" if has_prevention else ""),
        )

    if msg_has_error:
        # User pasted an error but answer may not have a clear fix yet
        return MemorySignificance(
            score=0.75,
            memory_type="bug_fix",
            should_store=True,
            reason="Bug/error reported",
        )

    # --- Code patterns and conventions ---

    if _CODE_PATTERN_PATTERNS.search(combined):
        return MemorySignificance(
            score=0.85,
            memory_type="code_pattern",
            should_store=True,
            reason="Code pattern, convention, or style guidance",
        )

    # --- User preferences ---

    if _PREFERENCE_PATTERNS.search(message):
        return MemorySignificance(
            score=0.8,
            memory_type="preference",
            should_store=True,
            reason="User stated a preference or instruction",
        )

    # --- Decisions ---

    if _DECISION_PATTERNS.search(combined):
        return MemorySignificance(
            score=0.9,
            memory_type="decision",
            should_store=True,
            reason="Contains decision or commitment",
        )

    # --- Factual ---

    if _FACTUAL_PATTERNS.search(combined):
        return MemorySignificance(
            score=0.6,
            memory_type="factual",
            should_store=True,
            reason="Contains specific factual information",
        )

    # --- Noise filters ---

    if _NOISE_PATTERNS.search(message) and len(message.split()) < 8:
        return MemorySignificance(
            score=0.05,
            memory_type="noise",
            should_store=False,
            reason="Conversational noise (greeting, acknowledgment)",
        )

    if len(message.split()) < 5:
        return MemorySignificance(
            score=0.15,
            memory_type="noise",
            should_store=False,
            reason="Too brief to be significant",
        )

    no_info_phrases = ["don't have", "no information", "not available", "no context"]
    if any(p in answer.lower() for p in no_info_phrases) and len(answer) < 200:
        return MemorySignificance(
            score=0.1,
            memory_type="noise",
            should_store=False,
            reason="No useful information exchanged",
        )

    # --- Design discussions ---

    if features.get("is_design_oriented", 0) > 0.5:
        return MemorySignificance(
            score=0.7,
            memory_type="conceptual",
            should_store=True,
            reason="Design or architecture discussion",
        )

    # --- Default ---

    return MemorySignificance(
        score=0.4,
        memory_type="conversational",
        should_store=True,
        reason="Standard interaction",
    )
