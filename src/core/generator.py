"""Module for generating unique IDs based on timestamps and random numbers."""

import datetime
import secrets


def generate_id_with_random_number() -> str:
    """Generate a unique ID using a timestamp (without year) and a random number.

    The timestamp uses month, day, hour, minute, second, and microsecond in UTC.
    A cryptographically secure random number between 0 and 65 is appended
    to ensure uniqueness.

    Returns:
        str: The generated unique ID.

    """
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%m%d%H%M%S%f")

    random_number = secrets.randbelow(66)

    return f"{timestamp}{random_number}"


if __name__ == "__main__":
    id_example = generate_id_with_random_number()
