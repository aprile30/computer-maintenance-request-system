from django import forms

from .models import Computer, IssueCategory, Location, MaintenanceRequest, User


class BS:
    """Adds Bootstrap classes to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "form-select"
            else:
                w.attrs["class"] = "form-control"


class RequestForm(BS, forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["computer", "category", "title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["computer"].queryset = (
            Computer.objects.exclude(condition_status="retired").select_related("location")
        )


class ReviewForm(BS, forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["priority", "assigned_to", "review_note"]
        widgets = {"review_note": forms.Textarea(attrs={"rows": 3})}
        labels = {"assigned_to": "Assign to technician", "review_note": "Remarks / reason"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(role="technician", is_active=True)
        self.fields["assigned_to"].empty_label = "-- select technician --"


class TechUpdateForm(BS, forms.Form):
    status = forms.ChoiceField(
        choices=[("in_progress", "In Progress"), ("on_hold", "On Hold"), ("completed", "Completed")]
    )
    remarks = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def clean(self):
        data = super().clean()
        if data.get("status") == "completed" and not data.get("remarks"):
            self.add_error("remarks", "Please add repair notes before marking the job as completed.")
        return data


class LocationForm(BS, forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "building", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ComputerForm(BS, forms.ModelForm):
    class Meta:
        model = Computer
        fields = ["property_no", "location", "brand", "model", "condition_status"]


class CategoryForm(BS, forms.ModelForm):
    class Meta:
        model = IssueCategory
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class UserForm(BS, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text="Required for a new user. On edit, leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department", "is_active"]

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not data.get("password"):
            self.add_error("password", "Password is required for a new user.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
