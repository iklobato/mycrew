"""Issue handling exceptions."""


class IssueHandlerError(Exception):
    """Base exception for issue handling."""

    pass


class UnsupportedSourceError(IssueHandlerError):
    """Raised when issue URL is not from a supported source."""

    pass


class IssueFetchError(IssueHandlerError):
    """Raised when API call to fetch issue fails."""

    pass


class IssueParseError(IssueHandlerError):
    """Raised when issue URL cannot be parsed."""

    pass
