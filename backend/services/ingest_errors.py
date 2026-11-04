"""Expected recipe import failures, kept separate from database/programming errors."""


class IngestError(Exception):
    """Base error callers can present to the person importing a recipe."""


class SourceError(IngestError):
    """The source could not be read within the import limits."""


class ExtractionError(IngestError):
    """The source did not contain a valid recipe."""


class ProviderNotConfiguredError(IngestError):
    """An optional service is needed for this source but has no configuration."""


class ProviderError(IngestError):
    """A configured model service failed or returned unusable output."""
