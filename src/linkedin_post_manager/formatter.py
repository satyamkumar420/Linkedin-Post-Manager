"""Post formatting, hook optimization, readability scoring, and hashtag helpers."""

import re
from typing import Any, Optional

MAX_LINKEDIN_POST_CHARS = 3000
IDEAL_HOOK_MAX_CHARS = 140

POST_TEMPLATES = {
    "project-launch": """🚀 Excited to unveil what we've been building: {title}

The Problem:
{problem}

How we solved it:
{solution}

Key features & tech stack:
• {feature_1}
• {feature_2}
• {feature_3}

Check it out and let me know your thoughts in the comments! 👇

{hashtags}""",
    "tech-learning": """💡 1 key lesson I learned this week while working on {topic}:

{breakdown}

3 takeaways for developers:
1️⃣ {takeaway_1}
2️⃣ {takeaway_2}
3️⃣ {takeaway_3}

Have you run into this before? How do you tackle it?

{hashtags}""",
    "career-milestone": """🎉 Today marks a significant milestone: {milestone}!

Looking back at where it started:
{reflection}

A huge thank you to everyone who supported this journey. On to the next chapter! 🚀

{hashtags}""",
    "hot-take": """🔥 Unpopular opinion: {opinion}

Here's why most people get this wrong:
{argument}

Agree or disagree? Let's discuss below 👇

{hashtags}""",
}


def analyze_post_structure(content: str) -> dict[str, Any]:
    """Analyze LinkedIn post readability, length, hook length, and hashtags."""
    cleaned = content.strip()
    char_count = len(cleaned)
    words = cleaned.split()
    word_count = len(words)

    # First paragraph / hook line (before first newline)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    first_line = lines[0] if lines else ""
    hook_chars = len(first_line)

    # Extract hashtags
    hashtags = re.findall(r"#\w+", cleaned)
    hashtag_count = len(hashtags)

    # Evaluation
    warnings = []
    tips = []

    if char_count > MAX_LINKEDIN_POST_CHARS:
        warnings.append(
            f"Exceeds maximum LinkedIn limit ({char_count}/{MAX_LINKEDIN_POST_CHARS} chars)."
        )
    elif char_count > 2200:
        tips.append("Consider trimming slightly. Posts between 900-1600 characters perform best.")
    elif char_count < 150:
        tips.append("Very short post. Adding context or a story can boost reach.")

    if hook_chars > IDEAL_HOOK_MAX_CHARS:
        tips.append(
            f"Your opening hook is {hook_chars} chars. Keep the first line under 140 chars "
            "so it is fully visible before LinkedIn's '...see more' button."
        )

    if hashtag_count > 6:
        tips.append("You have more than 6 hashtags. 3 to 5 targeted hashtags give optimal reach.")
    elif hashtag_count == 0:
        tips.append("Add 3-5 relevant hashtags at the bottom to improve discoverability.")

    # Readability pacing check (paragraph density)
    avg_line_words = word_count / max(len(lines), 1)
    if avg_line_words > 25:
        tips.append("Text has long paragraphs. Break them into 1-2 sentence lines for mobile readability.")

    read_time_seconds = int((word_count / 200) * 60)

    return {
        "character_count": char_count,
        "max_characters": MAX_LINKEDIN_POST_CHARS,
        "word_count": word_count,
        "estimated_read_time": f"{read_time_seconds}s",
        "hook_text": first_line,
        "hook_character_count": hook_chars,
        "hook_status": "optimal" if hook_chars <= IDEAL_HOOK_MAX_CHARS else "too_long",
        "hashtags": hashtags,
        "hashtag_count": hashtag_count,
        "warnings": warnings,
        "recommendations": tips,
        "score": max(100 - (len(warnings) * 30 + len(tips) * 10), 40),
    }


def format_linkedin_post(
    raw_text: str,
    tone: str = "professional",
    add_cta: bool = True,
    hashtags: Optional[list[str]] = None,
) -> str:
    """Format raw text with proper spacing, readable spacing, and optional CTA."""
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return raw_text

    formatted_paragraphs = []
    for i, p in enumerate(paragraphs):
        # Format list lines if bulleted
        sublines = p.splitlines()
        clean_lines = []
        for line in sublines:
            line_str = line.strip()
            if line_str.startswith(("- ", "* ", "• ")):
                clean_lines.append(f"• {line_str[2:].strip()}")
            else:
                clean_lines.append(line_str)
        formatted_paragraphs.append("\n".join(clean_lines))

    result = "\n\n".join(formatted_paragraphs)

    if add_cta and "👇" not in result and "?" not in formatted_paragraphs[-1]:
        cta_options = {
            "professional": "What are your thoughts on this? I'd love to hear your perspective below 👇",
            "casual": "Have you experienced something similar? Let me know in the comments! 👇",
            "technical": "How do you approach this in your tech stack? Drop your tips below 👇",
        }
        chosen_cta = cta_options.get(tone.lower(), cta_options["professional"])
        result += f"\n\n{chosen_cta}"

    if hashtags:
        clean_tags = []
        for tag in hashtags:
            clean_tag = tag.strip().lstrip("#")
            if clean_tag:
                clean_tags.append(f"#{clean_tag}")
        if clean_tags:
            result += f"\n\n{' '.join(clean_tags)}"

    return result
