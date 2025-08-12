"""Database models for the user application.

This module defines models for various website components like SEO,
main page content, about us, gallery, and contact information.
"""

from django.db import models


class SEO(models.Model):
    """SEO settings for pages (title, description, keywords)."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    keyword = models.CharField(max_length=255)

    def __str__(self):
        """Return the title of the SEO configuration."""
        return self.title


class Main(models.Model):
    """Main page with images, a title, and a description."""

    slide = models.ImageField(upload_to="slides/")
    slide2 = models.ImageField(upload_to="slides/", blank=True, null=True)
    slide3 = models.ImageField(upload_to="slides/", blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    seo = models.OneToOneField(SEO, on_delete=models.CASCADE)

    def __str__(self):
        """Return the title of the main page content."""
        return self.title


class Block(models.Model):
    """Content block on the main page."""

    image = models.ImageField(upload_to="blocks/")
    title = models.CharField(max_length=255)
    description = models.TextField()
    main = models.OneToOneField(Main, on_delete=models.CASCADE)

    def __str__(self):
        """Return the title of the content block."""
        return self.title


class AboutUs(models.Model):
    """'About Us' page with an image, a gallery, and SEO."""

    image = models.ImageField(upload_to="about_us/")
    title = models.CharField(max_length=255)
    description = models.TextField()
    seo = models.OneToOneField(SEO, on_delete=models.CASCADE)

    def __str__(self):
        """Return the title of the 'About Us' page."""
        return self.title


class Gallery(models.Model):
    """Gallery linked to the 'About Us' page."""

    about_us = models.ForeignKey(AboutUs, on_delete=models.CASCADE)

    def __str__(self):
        """Return a string representation of the gallery."""
        return f"Gallery for {self.about_us.title}"


class Image(models.Model):
    """Image within a gallery."""

    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="gallery/")

    def __str__(self):
        """Return a string representation of the image."""
        return f"Image for {self.gallery.about_us.title}"


class Document(models.Model):
    """Document attached to the 'About Us' page."""

    document = models.FileField(upload_to="documents/")
    about_us = models.ForeignKey(AboutUs, on_delete=models.CASCADE)

    def __str__(self):
        """Return a string representation of the document."""
        return f"Document for {self.about_us.title}"


class ServiceStr(models.Model):
    """Service or tariff with an image and SEO."""

    is_tariff = models.BooleanField(default=False)
    image = models.ImageField(upload_to="services/")
    title = models.CharField(max_length=255)
    description = models.TextField()
    seo = models.OneToOneField(SEO, on_delete=models.CASCADE)

    def __str__(self):
        """Return the title of the service or tariff."""
        return self.title


class Contact(models.Model):
    """Contact information for the organization."""

    full_name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    # Fix: Removed null=True. For string fields, `blank=True` is sufficient.
    url = models.URLField(blank=True)
    address = models.CharField(max_length=255)
    # Fix: Removed null=True. For string fields, `blank=True` is sufficient.
    map = models.TextField(blank=True)
    email = models.EmailField()
    seo = models.OneToOneField(SEO, on_delete=models.CASCADE)

    def __str__(self):
        """Return the full name of the organization."""
        return self.full_name
