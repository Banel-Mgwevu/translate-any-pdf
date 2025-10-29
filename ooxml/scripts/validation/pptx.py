from .base import BaseValidator

class PPTXSchemaValidator(BaseValidator):
    def __init__(self):
        super().__init__()
    
    def validate(self, doc):
        return True
