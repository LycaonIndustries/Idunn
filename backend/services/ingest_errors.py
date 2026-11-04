"""Expected recipe import failures, kept separate from database/programming errors."""

# Separate user-facing input errors from internal system crashes.
# This prevents leaking internal tracebacks to the client UI.


class IngestError(Exception):
    """Base error callers can present to the person importing a recipe."""


# Raise when external websites time out, block requests, or return oversized data.
class SourceError(IngestError):
    """The source could not be read within the import limits."""


# Raise when the supplied text, image, or video does not contain a coherent recipe.
class ExtractionError(IngestError):
    """The source did not contain a valid recipe."""


# Raise when a user tries an AI ingestion route without providing their BYOK API credentials.
class ProviderNotConfiguredError(IngestError):
    """An optional service is needed for this source but has no configuration."""


# Raise when a remote LLM API fails with 5xx status or rate limits.
class ProviderError(IngestError):
    """A configured model service failed or returned unusable output."""
