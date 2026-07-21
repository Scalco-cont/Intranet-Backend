import re
import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    'p', 'br', 'h1', 'h2', 'h3',
    'strong', 'em', 'u', 's', 'blockquote',
    'ol', 'ul', 'li', 'a', 'span',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target', 'rel'],
    'span': ['style'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

_css_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'background-color'])


def sanitize_html(html: str) -> str:
    """Remove tags/atributos perigosos do HTML gerado pelo editor rich-text,
    mantendo apenas a formatação suportada pela toolbar do ReactQuill."""
    if not html:
        return html
    # Remove script and style tags entirely (including their content)
    html = re.sub(r'<\s*script[^>]*>.*?</\s*script\s*>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<\s*style[^>]*>.*?</\s*style\s*>', '', html, flags=re.IGNORECASE | re.DOTALL)

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
    )
