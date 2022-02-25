from unicodedata import name
from django.db import models

class Person(models.Model):
    """Model definition for Person."""

    # TODO: Define fields here
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombres', max_length=200)
    last_name = models.CharField('Apellidos', max_length=200)
    image = models.ImageField('Imagen de Perfil')

    class Meta:
        """Meta definition for Person."""

        verbose_name = 'Person'
        verbose_name_plural = 'Persons'

    def __str__(self):
        """Unicode representation of Person."""
        return self.name

