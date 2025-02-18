# models.py

from django.db import models

class Nave(models.Model):
    puerto_choices = [
        ('Valparaíso', 'Valparaíso'),
        ('San Antonio', 'San Antonio'),
    ]

    puerto = models.CharField(max_length=20, choices=puerto_choices)
    nombre_nave = models.CharField(max_length=255, null=True, blank=True)
    fecha = models.CharField(max_length=255, null=True, blank=True)
    hora = models.CharField(max_length=255, null=True, blank=True)
    metros = models.CharField(max_length=255, null=True, blank=True)
    operacion = models.CharField(max_length=255, null=True, blank=True)
    posicion = models.CharField(max_length=255, null=True, blank=True)
    sitio = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nombre_nave
