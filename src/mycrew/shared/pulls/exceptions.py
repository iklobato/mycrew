"""PR exceptions."""

from mycrew.shared.issues.exceptions import IssueHandlerError


class PRHandlerError(IssueHandlerError):
    """Base exception for PR handling."""

    pass


class PRParseError(PRHandlerError):
    """Raised when PR URL cannot be parsed."""

    pass


class PRFetchError(PRHandlerError):
    """Raised when API call to fetch PR fails."""

    pass


class UnsupportedSourceError(PRHandlerError):
    """Raised when PR URL is not from a supported source."""

    pass
