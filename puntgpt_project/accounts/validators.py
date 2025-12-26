import re
from django.core.exceptions import ValidationError

class StrongPasswordValidator:
    def validate(self, password, user=None):
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'

        if not re.match(pattern, password):
            raise ValidationError(
                "Password must contain at least 8 characters, including uppercase, lowercase, number, and special character."
            )

    def get_help_text(self):
        return "Must include uppercase, lowercase, number, and special character."
