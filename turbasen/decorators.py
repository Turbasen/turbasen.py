def requires_object_id(func):
    def wrapper(self, *args, **kwargs):
        if self.object_id is None:
            raise TypeError("You cannot call this method on an object without a specified object ID.")
        return func(self, *args, **kwargs)
    return wrapper
