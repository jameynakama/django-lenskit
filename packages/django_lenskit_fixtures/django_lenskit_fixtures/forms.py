from __future__ import annotations

from django import forms


class FixtureExportForm(forms.Form):
    FORMAT_CHOICES = (
        ("json", "JSON"),
        ("yaml", "YAML"),
    )

    fmt = forms.ChoiceField(choices=FORMAT_CHOICES, initial="json")
    include_reverse = forms.BooleanField(required=False, initial=False)
    object_limit = forms.IntegerField(min_value=1, initial=5000)

    def clean_object_limit(self) -> int:
        value = int(self.cleaned_data["object_limit"])
        return max(1, value)
