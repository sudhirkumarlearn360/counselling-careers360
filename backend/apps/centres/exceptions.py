from apps.common.exceptions import DomainError


class CentreInvalid(DomainError):
    code = "invalid"


class CentreClosed(DomainError):
    code = "centre_closed"
    message = "This centre has closed and can't be changed."


class CentreNotPlanned(DomainError):
    code = "not_planned"
    message = "Only a planned centre can go live."


class CentreNotLive(DomainError):
    code = "not_live"
    message = "Only a live centre can be closed."
