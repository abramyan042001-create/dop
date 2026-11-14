from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Quote(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=200, blank=True, default="")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="quotes")
    tags = models.ManyToManyField(Tag, blank=True, related_name="quotes")

    class Meta:
        ordering = ["id"]
