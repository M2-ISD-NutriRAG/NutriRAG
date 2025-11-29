"""Console output utilities with colored formatting."""

from enum import Enum
from colorama import Fore, Style, init

# Initialize colorama once
init(autoreset=True)


class MessageType(Enum):
    """Enum for console message types."""

    INFO = "info"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    HEADER = "header"
    STAGE = "stage"
    HIGHLIGHT = "highlight"


def print_message(
    message_type: MessageType, message: str, width: int | None = None
) -> None:
    """Print a colored message to console.

    Args:
        message_type: Type of message (INFO, SUCCESS, ERROR, WARNING, HEADER, STAGE, HIGHLIGHT)
        message: The message text to display
        width: Width for separators (only used for HEADER and STAGE types, defaults to 60)

    Raises:
        ValueError: If width is specified for message types other than HEADER or STAGE
    """
    # Validate width parameter
    if width is not None and message_type not in (
        MessageType.HEADER,
        MessageType.STAGE,
    ):
        raise ValueError(
            f"Width parameter can only be used with HEADER or STAGE message types, "
            f"not with {message_type.value}"
        )

    color_map = {
        MessageType.INFO: Fore.CYAN,
        MessageType.SUCCESS: Fore.GREEN,
        MessageType.ERROR: Fore.RED,
        MessageType.WARNING: Fore.YELLOW,
        MessageType.HEADER: Fore.MAGENTA,
        MessageType.STAGE: Fore.BLUE,
        MessageType.HIGHLIGHT: Fore.BLUE,
    }

    color = color_map[message_type]

    if message_type in (MessageType.HEADER, MessageType.STAGE):
        separator_width = width if width is not None else 60
        separator = "=" * separator_width
        print(f"\n{color}{separator}{Style.RESET_ALL}")
        print(f"{color} {message}{Style.RESET_ALL}")
        print(f"{color}{separator}{Style.RESET_ALL}")
    else:
        print(f"{color}{message}{Style.RESET_ALL}")
