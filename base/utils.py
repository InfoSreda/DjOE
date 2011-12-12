import datetime
import decimal
from django.db import models


DATETIME_FORMATS = ('%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%d')

def to_oe(value):
    if isinstance(value, datetime.datetime):
        value = value.strftime(DATETIME_FORMATS[0])
    elif isinstance(value, decimal.Decimal):
        value = str(value)
    elif isinstance(value, models.Model):
        value = value.pk
    return value

def django2openerp(obj):
    django_obj = dict()
    for k, value in obj.iteritems():
        django_obj[k] = to_oe(value)
    return django_obj

def openerp2django(obj, model):
    django_obj = dict()

    for k, value in obj.iteritems():
        field_type = model._meta.get_field_by_name(k)[0]
        if value == False and not isinstance(field_type,
                           (models.BooleanField, models.NullBooleanField)):
            value = None
        if isinstance(field_type, models.ForeignKey):
            if value:
                if isinstance(value, (list,tuple)):
                    pk, name = value[:2]
                else:
                    name, pk = None, value
                inst = field_type.rel.to(id=pk)
                inst.name = name
                value = inst
            else:
                value = None
        if isinstance(value, list) and isinstance(field_type,
                                                  (models.IntegerField)):
            # foreign key case, when  OE return  [id, name]
            value = value[0] if value else None

        if value and isinstance(field_type, (models.DateTimeField,
                                             models.DateField)):
            for dformat in DATETIME_FORMATS:
                try:
                    value = datetime.datetime.strptime(value, dformat)
                    break
                except ValueError:
                    continue
                    
        django_obj[k] = value
    return django_obj
