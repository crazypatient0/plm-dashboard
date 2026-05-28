"""EAI message categorization module.

Provides a standalone pure function to categorize EAI (Enterprise Application
Integration) status messages into predefined categories.
"""


def categorize_eai_message(eai_message: str | None) -> str:
    """Categorize an EAI message string into a predefined category.

    Args:
        eai_message: The EAI status message to categorize. May be None.

    Returns:
        One of:
        - 'Normal'             if eai_message is None, empty, or whitespace-only
        - 'StatusFlowError'    if message contains 'IW folgt nicht'
        - 'MissingOriginals'   if message contains 'alle Originale abgelegt'
        - 'Normal'             for any other non-empty message (fallback)
    """
    if not eai_message or not eai_message.strip():
        return "Normal"

    if "IW folgt nicht" in eai_message:
        return "StatusFlowError"

    if "alle Originale abgelegt" in eai_message:
        return "MissingOriginals"

    return "Normal"
