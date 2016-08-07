class DocumentNotFound(Exception):
    """Thrown when a request for a document with a given object id isn't found in Turbasen"""
    pass

class Unauthorized(Exception):
    """Thrown when a request returns a HTTP 401 Unathorized or 403 Forbidden status code"""
    pass

class InvalidDocument(Exception):
    """Thrown when updating or creating a document with invalid data"""
    pass

class ServerError(Exception):
    """Thrown when a request results in a 5xx server error response"""
    pass
