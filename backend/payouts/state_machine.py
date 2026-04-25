VALID_TRANSITIONS = {
    "pending": ["processing"],
    "processing": ["completed", "failed"],
}


def can_transition(current_status, new_status):
    """Return True only if the transition is explicitly allowed."""
    allowed = VALID_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def transition_or_raise(current_status, new_status):
    """Perform the transition check and raise if illegal."""
    if not can_transition(current_status, new_status):
        raise InvalidTransitionError(
            f"Cannot transition from '{current_status}' to '{new_status}'"
        )


class InvalidTransitionError(Exception):
    pass