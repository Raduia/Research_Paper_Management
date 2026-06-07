from django.core.exceptions import ValidationError

def validate_pdf(file):
    if not file.name.endswith('.pdf'):
        raise ValidationError('Only PDF files are allowed.')

    if file.size > 10 * 1024 * 1024:
        raise ValidationError('PDF size cannot exceed 10MB.')
