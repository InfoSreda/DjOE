from StringIO import StringIO
from django.db import models
from django import forms
from django.core.urlresolvers import reverse


class OpenERPBooleanField(models.NullBooleanField):

    def __init__(self, *args, **kwargs):
        # jump over NullBoolean hardcoded null and blank
        return super(models.NullBooleanField, self).__init__(*args, **kwargs)

    ## def to_python(self, value):
    ##     if self.null:
    ##         return models.NullBooleanField.to_python(self, value)
    ##     return models.BooleanField.to_python(self, value)

    ## def formfield(self, **kwargs):
    ##     if self.null:
    ##         return models.NullBooleanField.formfield(self, **kwargs)
    ##     return models.BooleanField.formfield(self, **kwargs)


class OpenERPIntegerField(models.IntegerField):
    pass


class OpenERPFloatField(models.DecimalField, models.FloatField):

    def __init__(self, *args, **kwargs):
        self.digits = kwargs.pop('digits', None)
        if self.digits:
            kwargs['max_digits'] = self.digits[0]
            kwargs['decimal_places'] = self.digits[1]
            return super(OpenERPFloatField, self).__init__(*args, **kwargs)
        return models.FloatField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if self.digits:
            return models.DecimalField.to_python(self, value)
        return models.FloatField.to_python(self, value)

    def formfield(self, **kwargs):
        if self.digits:
            return models.DecimalField.formfield(self, **kwargs)
        return models.FloatField.formfield(self, **kwargs)


class OpenERPCharField(models.CharField):

    def __init__(self, *args, **kwargs):
        if not 'max_length' in kwargs:
            kwargs['max_length'] = 1024
        super(OpenERPCharField, self).__init__(*args, **kwargs)

class OpenERPTextField(models.TextField):
    pass

class OpenERPDateField(models.DateField):
    pass

class OpenERPDatetimeField(models.DateTimeField):
    pass

class OpenERPSelectionField(models.CharField):
    def __init__(self, *args, **kwargs):
        if not 'max_length' in kwargs:
            kwargs['max_length'] = 64
        super(OpenERPSelectionField, self).__init__(*args, **kwargs)

class OpenERPReferenceField(models.CharField):
    def __init__(self, *args, **kwargs):
        if not 'max_length' in kwargs:
            kwargs['max_length'] = 256
        super(OpenERPReferenceField, self).__init__(*args, **kwargs)


class OpenERPMany2oneField(models.ForeignKey):

    def contribute_to_related_class(self, cls, related):
        pass


class OneToManyDescriptor(models.related.ReverseSingleRelatedObjectDescriptor):

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        cache_name = self.field.get_cache_name()
        try:
            return getattr(instance, cache_name)
        except AttributeError:
            val = getattr(instance, self.field.attname)
            if val is None:
                # If NULL is an allowed value, return it.
                if self.field.null:
                    return None
                raise self.field.rel.to.DoesNotExist
            other_field = self.field.rel.get_related_field()
            if other_field.rel:
                params = {'%s__pk__in' % self.field.rel.field_name: val}
            else:
                params = {'%s__in' % self.field.rel.field_name: val}

            rel_mgr = self.field.rel.to._default_manager
            rel_objs = rel_mgr.filter(**params)
            setattr(instance, cache_name, rel_objs)
            return rel_obj

    def __set__(self, instance, values):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self._field.name)

        # If null=True, we can assign null here, but otherwise the value needs
        # to be an instance of the related class.
        if not values and not self.field.null:
            raise ValueError('Cannot assign None or []: "%s.%s" does not allow null values.' %
                                (instance._meta.object_name, self.field.name))
        if values is None:
            values = []
        if not isinstance(values, (list, tuple)):
            raise ValueError('Cannot assign "%r": "%s.%s" must be a list.' %
                                (values, instance._meta.object_name,
                                 self.field.name))
        
        for value in values:
            if not isinstance(value, self.field.rel.to):
                raise ValueError('Cannot assign "%r": "%s.%s" must be a "%s"'\
                        ' instance.' % (value, instance._meta.object_name,
                         self.field.name, self.field.rel.to._meta.object_name))
        if values is None:
            related = getattr(instance, self.field.get_cache_name(), None)

            if related:
                cache_name = self.field.related.get_cache_name()
                try:
                    delattr(related, cache_name)
                except AttributeError:
                    pass

        vals = []
        for value in values:
            # Set the value of the related field
            try:
                val = getattr(value, self.field.rel.get_related_field().attname)
            except AttributeError:
                val = None
            vals.append(val)
        setattr(instance, self.field.attname, vals)

        setattr(instance, self.field.get_cache_name(), values)


class OpenERPOne2manyField(models.ForeignKey):

    def contribute_to_class(self, cls, name):
        super(models.ForeignKey, self).contribute_to_class(cls, name)
        setattr(cls, self.name, OneToManyDescriptor(self))
        if isinstance(self.rel.to, basestring):
            target = self.rel.to
        else:
            target = self.rel.to._meta.db_table
        cls._meta.duplicate_targets[self.column] = (target, "o2m")
    
    def contribute_to_related_class(self, cls, related):
        pass

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        defaults = {
            'form_class': forms.ModelMultipleChoiceField,
            'queryset': self.rel.to._default_manager,
            'to_field_name': self.rel.field_name,
        }
        defaults.update(kwargs)
        return super(OpenERPOne2manyField, self).formfield(**defaults)


class OpenERPMany2manyField(OpenERPOne2manyField):
    pass

class OEReverseManyRelatedObjectsDescriptor(models.fields.related.ReverseManyRelatedObjectsDescriptor):

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        vals = {self.field.name:[(6, 0, [v.pk for v in value])]}
        instance.__class__.objects.oe_write([instance.id], vals)


## class OpenERPMany2manyField(models.ManyToManyField):

##     def contribute_to_class(self, cls, name):
##         super(OpenERPMany2manyField, self).contribute_to_class(cls, name)
##         # Add the descriptor for the m2m relation
##         setattr(cls, self.name, OEReverseManyRelatedObjectsDescriptor(self))


class OEFieldFile(models.fields.files.FieldFile):

    def __init__(self, instance, field, name):
        super(models.fields.files.FieldFile, self).__init__(None, name)
        self.instance = instance
        self.field = field
        self._committed = True

    def _get_file(self):
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


class OpenERPBinaryField(models.FileField):
    
    attr_class = OEFieldFile

    def __init__(self, *args, **kwargs):
        # fake
        kwargs['upload_to'] = '.'
        return super(OpenERPBinaryField, self).__init__(*args, **kwargs)
