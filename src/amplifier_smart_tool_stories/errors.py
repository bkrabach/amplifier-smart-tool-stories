class StoriesError(Exception):
    def __init__(self, code, message, remedy="Check the capability help and supplied input."):
        super().__init__(message)
        self.code, self.message, self.remedy = code, message, remedy

    def public(self):
        return {
            "status": "failed",
            "error": {"code": self.code, "message": self.message, "remedy": self.remedy},
        }


def require(condition, message, code="invalid_input"):
    if not condition:
        raise StoriesError(code, message)
