from django import forms


class DownloadForm(forms.Form):
    url = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Paste YouTube link here (e.g. https://youtu.be/...)',
            'class': 'modern-input',
            'autocomplete': 'off',
            'aria-label': 'YouTube Video URL',
        }),
        label=False,
    )
