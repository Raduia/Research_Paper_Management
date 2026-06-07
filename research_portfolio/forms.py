from django import forms
from django.contrib.auth.models import User

from .models import Evaluation, Paper


class PaperForm(forms.ModelForm):
    class Meta:
        model = Paper
        fields = [
            'title',
            'authors',
            'journal',
            'publication_date',
            'doi',
            'abstract',
            'category',
            'journal_index',
            'supervisor',
            'deadline',
            'pdf',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter paper title'}),
            'authors': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author names separated by commas'}),
            'journal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Journal or conference name'}),
            'publication_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'doi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digital Object Identifier'}),
            'abstract': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Short abstract or summary'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'journal_index': forms.Select(attrs={'class': 'form-select'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supervisor'].queryset = User.objects.filter(profile__role='supervisor')
        self.fields['supervisor'].required = False
        self.fields['category'].required = False
        self.fields['journal_index'].required = False
        self.fields['pdf'].required = False


class EvaluationForm(forms.ModelForm):
    score_attrs = {'class': 'form-control', 'min': 0, 'max': 100, 'step': 1}

    class Meta:
        model = Evaluation
        fields = [
            'methodology_score',
            'innovation_score',
            'writing_score',
            'technical_score',
            'feedback',
        ]
        labels = {
            'methodology_score': 'Methodology score',
            'innovation_score': 'Innovation score',
            'writing_score': 'Writing and presentation score',
            'technical_score': 'Technical depth score',
        }
        widgets = {
            'methodology_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 1}),
            'innovation_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 1}),
            'writing_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 1}),
            'technical_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 1}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Feedback, requested changes, and next steps'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field in ['methodology_score', 'innovation_score', 'writing_score', 'technical_score']:
            value = cleaned_data.get(field)
            if value is not None and not 0 <= value <= 100:
                self.add_error(field, 'Score must be between 0 and 100.')
        return cleaned_data
