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


def clean_markdown_links(text: str) -> str:
    """Convert markdown links [Label](URL) to plain text representation suitable for LinkedIn.

    If Label is identical to URL or URL without protocol, returns URL.
    Otherwise returns 'Label: URL'.
    """
    def _repl(match: re.Match) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        clean_lbl = label.replace("http://", "").replace("https://", "").rstrip("/")
        clean_u = url.replace("http://", "").replace("https://", "").rstrip("/")
        if clean_lbl == clean_u:
            return url
        return f"{label}: {url}"

    return re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", _repl, text)


def escape_linkedin_commentary(text: str) -> str:
    """Escape reserved characters for LinkedIn Little Text format in commentary.

    LinkedIn's Posts API uses 'Little Text' format for commentary.
    According to official LinkedIn documentation:
    Reserved characters: \\ | { } @ [ ] ( ) < > * _ ~

    CRITICAL: When LinkedIn API encounters unescaped reserved characters like '(',
    it attempts to parse them as Little Text elements (e.g. mentions). When parsing
    fails, LinkedIn SILENTLY TRUNCATES/DROPS all subsequent content in the post!
    This causes posts to be cut off at the first parenthesis without a '...see more' button.

    This function:
    1. Cleans markdown links [label](url) to avoid broken Little Text element parsing.
    2. Preserves valid LinkedIn mentions @[Display Name](urn:li:...) if present.
    3. Escapes all Little Text reserved characters with a backslash.
    """
    if not text:
        return text

    # Step 1: Normalize and clean markdown links
    text = clean_markdown_links(text)

    # Step 2: Preserve any valid Little Text mentions: @[Display Name](urn:li:person/organization:...)
    mentions: list[str] = []

    def _preserve_mention(m: re.Match) -> str:
        mentions.append(m.group(0))
        return f"__LINKEDIN_MENTION_{len(mentions)-1}__"

    text = re.sub(
        r"@\[[^\]]+\]\(urn:li:(?:person|organization):\w+\)",
        _preserve_mention,
        text,
    )

    # Step 3: Escape backslashes first
    text = text.replace("\\", "\\\\")

    # Step 4: Escape Little Text reserved characters: | { } @ [ ] ( ) < > * _ ~
    reserved_pattern = r"([|{}@\[\]()<>\*\_~])"
    text = re.sub(reserved_pattern, r"\\\1", text)

    # Step 5: Restore preserved mentions
    for idx, mention in enumerate(mentions):
        text = text.replace(f"__LINKEDIN_MENTION_{idx}__", mention)

    return text

