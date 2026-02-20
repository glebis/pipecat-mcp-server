"""Port interface for the voice agent child process."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VoiceAgentProcessPort(Protocol):
    """Protocol for managing the voice agent child process lifecycle."""

    def start(self) -> str | None:
        """Start the voice agent process.

        Returns:
            None on success, or an error message string.

        """
        ...

    def stop(self) -> None:
        """Stop the voice agent process."""
        ...

    async def check_health(self, delay: float = 1.0) -> str | None:
        """Check if the process is healthy after startup.

        Returns:
            None if healthy, or an error message string.

        """
        ...

    async def send_command(self, cmd: str, **kwargs) -> dict:
        """Send a command and wait for response.

        Args:
            cmd: Command name.
            **kwargs: Command arguments.

        Returns:
            Response dict from the child process.

        """
        ...
