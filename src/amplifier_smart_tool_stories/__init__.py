"""Stories public library; importing this module never initializes a model."""

from .errors import StoriesError
from .lib import Stories

__all__ = ["Stories", "StoriesError"]
