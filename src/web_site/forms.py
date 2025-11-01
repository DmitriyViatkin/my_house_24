"""Forms for the web_site Django application."""

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import inlineformset_factory
from django.forms import modelformset_factory

from .models import SEO
from .models import AboutUs
from .models import Block
from .models import Contact
from .models import Document
from .models import Gallery
from .models import Image
from .models import Main
from .models import ServiceStr


class ContactForm(forms.ModelForm):
    """Form for creating and updating Contact model instances."""

    class Meta:
        """Metadata for the ContactForm class."""

        model = Contact
        fields = [
            "full_name",
            "title",
            "description",
            "location",
            "phone",
            "url",
            "address",
            "map",
            "email",
        ]
        labels = {
            "full_name": "ФИО",
            "title": "Заголовок",
            "description": "Короткое описание",
            "location": "Локация",
            "phone": "Телефон",
            "url": "Ссылка на коммерческий сайт",
            "address": "Адрес",
            "map": "Карта",
            "email": "Емейл",
        }
        widgets = {
            "description": forms.Textarea(
                attrs={"class": "wysihtml5 form-control", "rows": 7}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите ФИО"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Локацию"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Телефон"}
            ),
            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите URL",
                }
            ),
            "address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Адрес"}
            ),
            "map": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите карту/ссылку",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите Email",
                }
            ),
        }


class TariffForm(forms.ModelForm):
    """Form for creating and updating tariff-related ServiceStr instances."""

    class Meta:
        """Metadata for TariffForm."""

        model = ServiceStr
        fields = ["image", "title", "description"]
        labels = {"image": "", "title": "", "description": ""}
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "wysihtml5 form-control", "rows": 7}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
        }

    def save(self, *, commit=True):
        """Save the form and mark instance as tariff before commit."""
        instance = super().save(commit=False)
        instance.is_tariff = True
        if commit:
            instance.save()
        return instance


TariffFormSet = modelformset_factory(
    ServiceStr, form=TariffForm, extra=0, can_delete=True
)


class ServiceForms(forms.ModelForm):
    """Form for creating and updating non-tariff ServiceStr instances."""

    class Meta:
        """Metadata for ServiceForms."""

        model = ServiceStr
        fields = ["image", "title", "description"]
        labels = {"image": "", "title": "", "description": ""}
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "wysihtml5 form-control", "rows": 7}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
        }

    def save(self, *, commit=True):
        """Save the form and mark instance as non-tariff before commit."""
        instance = super().save(commit=False)
        instance.is_tariff = False
        if commit:
            instance.save()
        return instance


ServiceFormSet = modelformset_factory(
    ServiceStr, form=ServiceForms, extra=0, can_delete=True
)


class ImageForm(forms.ModelForm):
    """Form for uploading and editing Image model instances."""

    class Meta:
        """Metadata for ImageForm."""

        model = Image
        fields = ("image",)
        widgets = {"image": forms.FileInput(attrs={"class": "form-control"})}


MainGalleryFormSet = inlineformset_factory(
    Gallery, Image, form=ImageForm, extra=0, can_delete=True, fk_name="gallery"
)

AdditionalGalleryFormSet = inlineformset_factory(
    Gallery, Image, form=ImageForm, extra=0, can_delete=True, fk_name="gallery"
)


class FormDocument(forms.ModelForm):
    """Form for creating and editing Document model instances."""

    class Meta:
        """Metadata for FormDocument."""

        model = Document
        fields = ["document", "title"]
        labels = {
            "title": "Название",
            "document": "PDF, JPG (макс. размер 20 Mb)",
        }
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
        }


DocumentFormSet = inlineformset_factory(
    AboutUs,
    Document,
    form=FormDocument,
    fields=("document", "title"),
    extra=1,
    can_delete=True,
)


class FormAboutUs(forms.ModelForm):
    """Form for editing the AboutUs section content."""

    class Meta:
        """Metadata for FormAboutUs."""

        model = AboutUs
        fields = ["image", "title", "description", "title2", "description2"]
        labels = {
            "image": "Фото директора",
            "title": "Заголовок",
            "description": "Краткий текст",
            "title2": "Заголовок",
            "description2": "Краткий текст",
        }
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
            "description": forms.Textarea(attrs={"class": "wysihtml5 form-control"}),
            "title2": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
            "description2": forms.Textarea(attrs={"class": "wysihtml5 form-control"}),
        }


class FormSEO(forms.ModelForm):
    """Form for managing SEO metadata."""

    class Meta:
        """Metadata for FormSEO."""

        model = SEO
        fields = ["title", "description", "keyword"]
        labels = {
            "title": "Title",
            "description": "Description",
            "keyword": "Keywords",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите Title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Введите Description",
                }
            ),
            "keyword": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": ("Введите Keywords (через запятую)"),
                }
            ),
        }


class FormMain(forms.ModelForm):
    """Form for managing main page slides and text."""

    class Meta:
        """Metadata for FormMain."""

        model = Main
        fields = ["slide", "slide2", "slide3", "title", "description"]
        labels = {
            "slide": "Слайд 1",
            "slide2": "Слайд 2",
            "slide3": "Слайд 3",
            "title1": "Заголовок",
            "description1": "Краткий текст",
        }
        widgets = {
            "description": CKEditorUploadingWidget(config_name="short_text"),
            "slide": forms.FileInput(attrs={"class": "form-control"}),
            "slide2": forms.FileInput(attrs={"class": "form-control"}),
            "slide3": forms.FileInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Введите заголовок"}
            ),
        }


class FormBlock(forms.ModelForm):
    """Form for editing Block model instances."""

    description = forms.CharField(
        widget=CKEditorUploadingWidget(config_name="short_text"), label="Описание"
    )

    class Meta:
        """Metadata for FormBlock."""

        model = Block
        fields = ["image", "title", "description"]
        labels = {"image": "Слайд", "title": "Заголовок", "description": "Описание"}

        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }

    def save(self, *, commit=True):
        """Save block instance, keeping existing image if not replaced."""
        instance = super().save(commit=False)
        if not self.cleaned_data.get("image") and self.instance.pk:
            instance.image = self.instance.image
        if commit:
            instance.save()
        return instance

    def clean_image(self):
        """Return existing image if none uploaded."""
        image = self.cleaned_data.get("image")
        if not image and self.instance and self.instance.pk:
            return self.instance.image
        return image


BlockFormSet = inlineformset_factory(
    Main, Block, form=FormBlock, extra=0, can_delete=True
)
