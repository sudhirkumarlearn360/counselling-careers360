from apps.common.exceptions import DomainError


class CounsellorInvalid(DomainError):
    code = "invalid"


class DeskClash(DomainError):
    code = "desk_clash"


class AlreadyPosted(DomainError):
    code = "already_posted"


class NoLivePosting(DomainError):
    code = "no_live_posting"
    message = "You aren't posted to a live centre today."
