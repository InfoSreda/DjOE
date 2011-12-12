from StringIO import StringIO
from django.db import models
from django.core.urlresolvers import reverse


class OEReverseManyRelatedObjectsDescriptor(models.fields.related.ReverseManyRelatedObjectsDescriptor):

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        vals = {self.field.name:[(6, 0, [v.pk for v in value])]}
        instance.__class__.objects.oe_write([instance.id], vals)


class OpenERPManyToManyField(models.ManyToManyField):

    def contribute_to_class(self, cls, name):
        super(OpenERPManyToManyField, self).contribute_to_class(cls, name)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, OEReverseManyRelatedObjectsDescriptor(self))


class OEFieldFile(models.fields.files.FieldFile):

    def __init__(self, instance, field, name):
        super(models.fields.files.FieldFile, self).__init__(None, name)
        self.instance = instance
        self.field = field
        self._committed = True

    def _get_file(self):
        #self._require_file()
        if not hasattr(self, '_file') or self._file is None:
            f = StringIO()
            base64data = self.instance.__class__.objects.oe_read(
                [self.instance.id], self.field.name)[0][self.field.name]
            data = base64.b64decode(base64data)
            f.write(data)
            f.seek(0)
            self._file = f
        return self._file

    def _set_file(self, file):
        self._file = file

    def _del_file(self):
        del self._file

    file = property(_get_file, _set_file, _del_file)

    def _get_url(self):
        #self._require_file()
        return reverse('djoe_base_media',
                       args=(self.instance.__class__._openerp_model,
                             self.instance.id, self.field.name))

    url = property(_get_url)

    def save(self, name, content, save=True):
        b64content = base64.encode(content.read())

        self.instance.__class__.objects.oe_write([self.instance.id],
                                                 {self.field.name:b64content})
        # Update the filesize cache
        self._size = content.size
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()

    save.alters_data = True

    def delete(self, save=True):
        self.instance.__class__.objects.oe_write([self.instance.id],
                                                 {self.field.name:False})

        self.name = None
        setattr(self.instance, self.field.name, self.name)

        # Delete the filesize cache
        if hasattr(self, '_size'):
            del self._size
        self._committed = False

        if save:
            self.instance.save()
    delete.alters_data = True


class OpenERPFileField(models.FileField):
    
    attr_class = OEFieldFile
