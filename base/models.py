import logging

from django.db import models
from django.forms.models import model_to_dict

from djoe.base.backends import connection, oe_session
from djoe.base.utils import django2openerp, openerp2django, to_oe
from djoe.base.query import OpenERPQuerySet
from djoe.base.fields import OpenERPManyToManyField, OpenERPFileField
import oe_pool


class OpenERPManager(models.Manager):

    def get_query_set(self):
        return OpenERPQuerySet(self.model)

    def oe_create(self, *args, **kwargs):
        return self.get_query_set().oe_create(*args, **kwargs)

    def oe_write(self, *args, **kwargs):
        return self.get_query_set().oe_write(*args, **kwargs)

    def oe_read(self, *args, **kwargs):
        return self.get_query_set().oe_read(*args, **kwargs)

    def oe_search(self, *args, **kwargs):
        return self.get_query_set().oe_search(*args, **kwargs)

    def oe_unlink(self, *args, **kwargs):
        return self.get_query_set().oe_unlink(*args, **kwargs)

    def oe_read_group(self, *args, **kwargs):
        return self.get_query_set().oe_read_group(*args, **kwargs)

    def context(self, *args, **kwargs):
        return self.get_query_set().context(*args, **kwargs)

    def oe_fields_view_get(self, *args, **kwargs):
        return self.get_query_set().oe_fields_view_get(*args, **kwargs)

    def oe_name_get(self, *args, **kwargs):
        return self.get_query_set().oe_name_get(*args, **kwargs)

    def execute(self, meth_name, *args):
        return self.get_query_set().execute(meth_name, *args)


def openerp_meth(meth):

    def wrapp(self, *args):
        res = oe_session.objects(self.__class__._openerp_model,
                                 meth.__name__, *args)
        return meth(self, res)
    return openerp_meth


FIELDS_MAP = {
    'char': models.CharField,
    'text': models.TextField,
    'integer': models.IntegerField,
    'date': models.DateTimeField,
    'datetime': models.DateTimeField,
    'time': models.DateTimeField,
    'selection': models.CharField,
    'binary': OpenERPFileField,
    'many2one': models.ForeignKey,
    'many2many': OpenERPManyToManyField,
    # TODO: make more correct
    #'one2many': models.IntegerField,
    # for float special select from FloatField or DecimalField
    # for bool special select from BooleanField or NullBooleanField
    # TODO: reference
    }


FIELD_ATTRS_MAP = {
    'string': 'verbose_name',
    'size': 'max_length',
    'relation': 'to',
    'help': 'help_text',
    'selection': 'choices'
    }


class OpenERPBaseModel(models.Model):

    objects = OpenERPManager()

    class Meta:
        abstract = True

    def __unicode__(self):
        if hasattr(self, 'name'):
            if not isinstance(self.name, basestring):
                return u'%r' % self.name
            return self.name or ''
        return u'%s object <%r>' % (self.__class__.__name__, self.pk)

    def save(self, force_insert=False, force_update=False, context=None):
        as_dict = model_to_dict(self, exclude=('id',))
        as_dict = django2openerp(as_dict)
        if self.id or force_update:
            res = self.__class__.objects.oe_write([self.id],
                                                  as_dict, context)
        else:
            print 'create!!!!!'
            self.id = self.__class__.objects.oe_create(as_dict, context)
        return self

    def delete(self, context=None, *args, **kwargs):
        return self.__class__.objects.oe_unlink([self.id], context)

    def name_get(self):
        if not self.pk:
            return ''
        print '^^^^^^^^^^^', self.__class__.objects.oe_name_get([self.id])
        return self.__class__.objects.oe_name_get([self.id])[0][1]


class OpenERPModelFactory(object):

    def __init__(self, model_name, deep=0, session=None, pool=None):
        self.model_name = model_name
        self.deep = deep
        if session is None:
            session = oe_session
        self.session = session
        if pool is None:
            pool = dict()
        if not pool:
            pool.update({ c._openerp_model: c for c in \
                          OpenERPBaseModel.__subclasses__() if \
                          hasattr(c, '_openerp_model')})
        self.pool = pool
        self.o2m_links = {}
        self.oe_readonly_fields = set()

    def _create_django_field(self, field_name, field_attrs):
        openerp_model = self.model_name
        oe_type = field_attrs.get('type')
        required = field_attrs.pop('required', False)
        kwargs = dict(null=not(required), blank=not(required))

        if field_name == 'id':
            kwargs['primary_key'] = True
        if oe_type == 'char':
            kwargs['max_length'] = 1024
        if oe_type == 'boolean':
            django_cls =  models.BooleanField if required else \
                                               models.NullBooleanField
        elif oe_type == 'float':
            digits = field_attrs.get('digits')
            if digits:
                django_cls = models.DecimalField
                kwargs['max_digits'] = digits[0]
                kwargs['decimal_places'] = digits[1]
            else:
                django_cls = models.FloatField
        else:
            django_cls = FIELDS_MAP.get(oe_type)
        if not django_cls and not oe_type == 'one2many':
            return
        kwargs.update( (FIELD_ATTRS_MAP[k], v) for k, v in \
                     field_attrs.iteritems() if k in FIELD_ATTRS_MAP )

        if oe_type == 'one2many':
            relation = field_attrs.get('relation')
            rel_model = self.pool.get(relation)
            if rel_model is None:
                if relation == openerp_model:
                    rel_model = 'self'
                else:
                    rel_model = OpenERPModelFactory(relation,
                             deep=self.deep, session=self.session,
                                 pool=self.pool).get_model(only_name=True)
            self.o2m_links[field_name] = rel_model
            return

        if oe_type in ('many2one', 'many2many'):
            relation = field_attrs.get('relation')
            if relation == openerp_model:
                to = 'self'
            else:
                to = self.pool.get(relation)
                if not to:
                    if self.deep is None or self.deep > 0:
                        deep = None if self.deep is None else self.deep - 1
                        to = OpenERPModelFactory(relation,
                                       deep=deep, session=self.session,
                                                 pool=self.pool).get_model()
                    else:
                        to = OpenERPModelFactory(relation,
                             deep=self.deep, session=self.session,
                                 pool=self.pool).get_model(only_name=True)
            kwargs['to'] = to
            model_name = openerp_model.rsplit('.', 1)[-1]
            rel_name = '%s_%s_set' % (model_name, field_name)
            if oe_type == 'many2one':
                kwargs['to_field'] = 'id'
                kwargs['related_name'] = rel_name
            else:
                #rel_name = field_attrs['related_columns'][1] if \
                #           'related_columns' in field_attrs else rel_name
                kwargs['related_name'] = rel_name

            field = django_cls(**kwargs)
            field.rel._oe_model = to
        elif oe_type == 'binary':
            # TODO: !!!
            kwargs['upload_to'] = '.'
        elif oe_type == 'selection':
            kwargs['max_length'] = 64
        field = django_cls(**kwargs)
        return field

    def get_fields(self, fields=None, exclude=None, all_oe_fields=None):
        ret_fields = dict()
        if all_oe_fields is None:
            all_oe_fields = self.session.objects(self.model_name, 'fields_get',
                                                 None,
                                             self.session.get_default_context())
        self.oe_readonly_fields = set()
        for field_name, field_attrs in all_oe_fields.iteritems():
            oe_type = field_attrs.get('type')
            if not oe_type:
                continue
            if fields and not field_name in fields:
                continue
            if exclude and field_name in exclude:
                continue
            field = self._create_django_field(field_name, field_attrs)
            if field_attrs.get('readonly', False):
                self.oe_readonly_fields.add(field_name)
            if field:
                ret_fields[field_name] = field
        return ret_fields

    def remake_fk(self, klass):
        for name, o2m_model in self.o2m_links.iteritems():
            if o2m_model == 'self':
                o2m_model = klass
            new_fields = []
            fk_kwargs = {}
            model_name = self.model_name.rsplit('.', 1)[-1]

            fk_field_name = '%s_id' % model_name
            for f in o2m_model._meta.local_fields[:]:
                if isinstance(f, models.ForeignKey):
                    if f.rel.to is klass:
                        fk_kwargs = dict(null=f.null, blank=f.blank, to=klass,
                                     related_name=name)
                        fk_field_name = f.name
                        continue
                new_fields.append(f)

            o2m_model._meta.local_fields = new_fields
            if not fk_kwargs:
                fk_kwargs = dict(null=True, blank=True, to=klass,
                                     related_name=name)

            f = models.ForeignKey(**fk_kwargs)
            f.contribute_to_class(o2m_model, fk_field_name)

            if hasattr(o2m_model._meta, '_field_cache'):
                del o2m_model._meta._field_cache
            if hasattr(o2m_model._meta, '_field_name_cache'):
                del o2m_model._meta._field_name_cache
        if hasattr (klass._meta, '_related_objects_cache'):
            del klass._meta._related_objects_cache

    def get_model(self, class_name=None, fields=None, exclude=None,
                  only_name=False, all_oe_fields=None):
        klass = self.pool.get(self.model_name)
        if klass:
            if not getattr(klass, '_openerp_only_name', False):
                return klass
            self.o2m_links = klass._openerp_o2m_links
            fields = self.get_fields(fields, exclude, all_oe_fields)
            # replace fields
            klass._meta.local_fields = [klass._meta.get_field_by_name('id')[0]]
            klass._meta.local_many_to_many = []
            if hasattr(klass._meta, '_field_cache'):
                del klass._meta._field_cache
            if hasattr(klass._meta, '_field_name_cache'):
                del klass._meta._field_name_cache

            for name, field in fields.iteritems():
                field.contribute_to_class(klass, name)
            klass._openerp_only_name = False
        else:
            if only_name:
                attrs = dict(name=models.CharField(max_length=256),
                         _openerp_only_name=True,
                         _openerp_readonly_fields=())
            else:
                attrs = self.get_fields(fields, exclude)
                attrs['_openerp_only_name'] = False
            attrs['__module__'] = self.__class__.__module__

            if not class_name:
                class_name = ''.join([el.capitalize() for el in \
                                  self.model_name.split('.')])
            klass = type(class_name, (OpenERPBaseModel,), attrs)

        if self.o2m_links:
            self.remake_fk(klass)
        klass._openerp_model = self.model_name
        klass._openerp_readonly_fields = self.oe_readonly_fields
        klass._openerp_session = self.session
        klass._openerp_pool = self.pool
        klass._openerp_o2m_links = self.o2m_links
        self.pool[self.model_name] = klass
        return klass


class ModelOpenERPBase(models.base.ModelBase):

    def __new__(cls, name, bases, attrs):
        super_new = super(ModelOpenERPBase, cls).__new__
        meta_ = attrs.get('Meta')
        if not meta_ or getattr(meta_, 'abstract', None):
            return super_new(cls, name, bases, attrs)
        # check meta attributes for OpenERP
        try:
            openerp_model = meta_.openerp_model
        except AttributeError:
            raise AttributeError('openerp_model attribute must be in class Meta')
        del attrs['Meta'].openerp_model

        attrs['_openerp_model'] = openerp_model
        openerp_fields = getattr(meta_, 'openerp_fields', [])
        if hasattr(attrs['Meta'], 'openerp_fields'):
            del attrs['Meta'].openerp_fields

        openerp_exclude = getattr(meta_, 'openerp_exclude', [])
        if hasattr(attrs['Meta'], 'openerp_exclude'):
            del attrs['Meta'].openerp_exclude

        if openerp_fields != False:
            oe_model = OpenERPModelFactory(openerp_model,
                                           session=oe_session,
                                           pool=oe_pool.pool)
            attrs.update(oe_model.get_fields(openerp_fields, openerp_exclude))

        klass = super_new(cls, name, bases, attrs)
        oe_pool.pool[openerp_model] = klass
        return klass


class OpenERPModel(OpenERPBaseModel):

    __metaclass__ = ModelOpenERPBase

    class Meta:
        abstract = True
