"""System prompt construction for the AI Video Captioning Agent.

This module contains the single authoritative system prompt sent to Fireworks AI.
"""

SYSTEM_PROMPT = (
    "You are an expert video analyst and caption writer.\n\n"
    "CRITICAL: You MUST return ONLY a valid JSON object. "
    "Do NOT include any analysis, explanations, markdown, or text outside the JSON.\n\n"
    "Your task:\n"
    "1. Analyze the video frames to understand the setting, subjects, actions, and details\n"
    "2. Generate FOUR captions in different styles\n"
    "3. Return ONLY the JSON object\n\n"
    "Caption styles:\n"
    "- formal: Professional, factual, documentary tone\n"
    "- sarcastic: Dry, ironic, witty observer\n"
    "- humorous_tech: Programming metaphors and tech jokes\n"
    "- humorous_non_tech: Everyday relatable humor, puns\n\n"
    "Rules:\n"
    "- Each caption must accurately describe the video content\n"
    "- Each caption must be distinctly different in tone\n"
    "- Keep captions 1-3 sentences each\n"
    "- Return ONLY valid JSON, nothing else\n"
    "- All four keys are mandatory and must be spelled exactly as shown\n"
    "- Use humorous_tech as the tech-humor key; do not use tech_humor\n\n"
    "Output format (return EXACTLY this structure):\n"
    '{"formal": "...", "sarcastic": "...", "humorous_tech": "...", "humorous_non_tech": "..."}'
)


def get_system_prompt() -> str:
    """Return the system prompt for the Fireworks AI model."""
    return SYSTEM_PROMPT


def build_user_prompt(
    transcript: str | None = None,
    style_hints: dict[str, str] | None = None,
    requested_styles: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Build the user message prompt with transcript and optional style hints.

    Args:
        transcript: Optional audio transcript from the video.
        style_hints: Optional dict mapping style names to additional instructions.

    Returns:
        The user prompt string.
    """
    styles = list(requested_styles or ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"])
    parts = [
        f"Analyze these video frames and generate {len(styles)} caption(s).\n"
        "Return ONLY one valid JSON object with exactly these mandatory keys: "
        f"{', '.join(styles)}. "
        "Do not wrap the JSON in markdown. Do not use tech_humor."
    ]
    if transcript:
        parts.append(f"\n\nAudio context: {transcript}")
    if style_hints:
        parts.append("\n\nStyle notes:")
        for style, hint in style_hints.items():
            parts.append(f"- {style}: {hint}")
    return "\n".join(parts)
