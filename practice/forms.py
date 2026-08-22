"""Dynamic forms used for short-exercise delivery."""

from django import forms


class ExerciseAnswerForm(forms.Form):
    """Validate one required answer for each delivered exercise question."""

    field_prefix = "question_"

    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions)
        for question in self.questions:
            self.fields[self.field_name(question.id)] = forms.TypedChoiceField(
                choices=enumerate(question.options_jsonb),
                coerce=int,
                empty_value=None,
                required=True,
                widget=forms.RadioSelect,
            )

    @classmethod
    def field_name(cls, question_id):
        return f"{cls.field_prefix}{question_id}"

    @classmethod
    def hint_field_name(cls, question_id):
        return f"hint_used_{question_id}"

    def answers(self):
        if not self.is_valid():
            raise ValueError("answers() requires a valid form")
        return {
            question.id: self.cleaned_data[self.field_name(question.id)]
            for question in self.questions
        }
