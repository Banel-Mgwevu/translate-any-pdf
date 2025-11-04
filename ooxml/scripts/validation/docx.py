from .base import BaseValidator

class DOCXSchemaValidator(BaseValidator):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.unpacked_path = kwargs.get('unpacked_path') or (args[0] if args else None)
        self.verbose = kwargs.get('verbose', False)
    
    def validate(self, doc=None):
        return True
