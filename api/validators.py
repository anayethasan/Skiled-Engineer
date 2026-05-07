from django.core.exceptions import ValidationError

def validate_file_size(file):
    max_size = 10
    in_KB = max_size * 1024 * 1024
    
    if file.size > in_KB:
        raise ValidationError(f"File size can't be lager the {max_size} MB.")