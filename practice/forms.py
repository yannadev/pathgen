"""Dynamic forms used for short-exercise delivery."""

from django import forms


class ExerciseAnswerForm(forms.Form):
    """Validate answer indexes while keeping questions optional for delivery."""

    field_prefix = "question_"

    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions)
        for question in self.questions:
            self.fields[self.field_name(question.id)] = forms.TypedChoiceField(
                choices=enumerate(question.options_jsonb),
                coerce=int,
                empty_value=None,
                required=False,
                widget=forms.RadioSelect,
            )

    @classmethod
    def field_name(cls, question_id):
        return f"{cls.field_prefix}{question_id}"
