import logging

from django.db import models
from django.db.models.sql.where import WhereNode, AND, OR
from django.db.models.query import QuerySet

from djoe.base.backends import connection, oe_session
from djoe.base.utils import django2openerp, openerp2django, to_oe

logger = logging.getLogger('openerp.query')


OP_MAP = {
    'exact': '=',
    'contains': 'like',
    'icontains': 'ilike',
    'in': 'in',
    'gt': '>',
    'lt': '<',
    'gte': '>=',
    'lte': '<='
    }


class OpenERPWhere(WhereNode):

    def add(self, data, connector):
        if not isinstance(data, (list, tuple)):
            super(models.sql.where.WhereNode, self).add(data, connector)
            return

        obj, lookup_type, value = data
        if hasattr(value, '__iter__') and hasattr(value, 'next'):
            # Consume any generators immediately, so that we can determine
            # emptiness and transform any non-empty values correctly.
            value = list(value)

        super(models.sql.where.WhereNode, self).add((obj, lookup_type,  value),
                                                    connector)

    def as_domain(self, node=None):
        if not self.children:
            return []
        if node is None:
            node = self
        result = []
        child_connector = AND
        length = len(node.children)
        for n, child in enumerate(node.children):
            if hasattr(child, 'as_sql'):
                domain = self.as_domain(child)
            else:
                # A leaf node in the tree.
                domain = self.make_atom(child, node.negated)
            if domain:
                result.extend(domain)
        if result and len(result) > 1 and node.connector == OR:
            result.insert(-2, '|')
        if result and node.negated:
            result.insert(0, '!')
        return result

    def make_atom(self, child, negated=False):
        """
        """
        lvalue, lookup_type, params = child
        # 
        if len(lvalue) > 1 and lvalue[-1] == 'id' and \
                                                   lvalue[-2].endswith('_set'):
            lvalue.pop(-2)
        field = '.'.join(lvalue)

        if lookup_type == 'range':
            return [(field, '>=', to_oe(params[0])),
                    (field, '<=', to_oe(params[1]))]
        if lookup_type == 'isnull':
            # TODO: More correct
            domain = [(field, '=', False)]
            if not params and not negated:
                domain.insert(0, '!')
            return domain
        try:
            oe_oper = OP_MAP[lookup_type]
        except KeyError:
            raise TypeError('Invalid lookup_type: %r' % lookup_type)
        return [(field, oe_oper, to_oe(params))]


class OpenERPQuery(models.sql.query.Query):

    def add_filter(self, filter_expr, connector=AND, negate=False, trim=False,
            can_reuse=None, process_extras=True, force_having=False):

        arg, value = filter_expr
        parts = arg.split('__')
        if not parts:
            raise FieldError("Cannot parse keyword query %r" % arg)

        # In OpenERP pk always is `id` field
        parts = ('id' if part == 'pk' else part for part in parts)
        parts = [part.split('_rel_+')[0] for part in parts]
        # Work out the lookup type and remove it from 'parts', if necessary.
        if len(parts) == 1 or parts[-1] not in self.query_terms:
            lookup_type = 'exact'
        else:
            lookup_type = parts.pop()

        if value is None:
            if lookup_type != 'exact':
                raise ValueError("Cannot use None as a query value")
            lookup_type = 'isnull'
            value = True
        elif callable(value):
            value = value()

        self.where.add((parts, lookup_type, value), connector)

    def get_oe_order_by(self):
        orders = []
        for field in self.order_by:
            if field == 'pk':
                field = 'id'
            orders.append('%s desc' % field[1:] if field.startswith('-')\
                              else field)
        return ', '.join(orders)

    def as_oe_search(self):
        limit = None
        if self.high_mark is not None:
            limit = self.high_mark - self.low_mark
        d = dict(domain= self.where.as_domain(), offset=self.low_mark,
                    limit=limit, order_by=self.get_oe_order_by(),
                    context=None, count=False)
        return d

    def __str__(self):
        return repr(self.as_oe_search())


class OpenERPQuerySet(QuerySet):

    def __init__(self, model, query=None, **kwargs):
        if query is None:
            query=OpenERPQuery(model, where=OpenERPWhere)
        super(OpenERPQuerySet, self).__init__(model, query=query, **kwargs)
        self.oe_context = None
        self.with_binary = False

    def distinct(self, *args, **kwargs):
        raise NotImplementedError('Method distinct() is not implemented'\
                                  ' in OpenERP ORM')
    def annotate(self, *args, **kwargs):
        raise NotImplementedError('Method annotate() is not implemented'\
                                  ' in OpenERP ORM')
    def aggregate(self, *args, **kwargs):
        raise NotImplementedError('Method aggregated() is not implemented'\
                                  ' in OpenERP ORM')
    def extra(self, *args, **kwargs):
        raise NotImplementedError('Method extra() is not implemented'\
                                  ' in OpenERP ORM')
    def select_related(self, *args, **kwargs):
        raise NotImplementedError('Method select_related() is not implemented'\
                                  ' in OpenERP ORM')
    def usage(self, *args, **kwargs):
        raise NotImplementedError('Method usage() is not implemented'\
                                  ' in OpenERP ORM')

    def execute(self, meth_name, *args):
        res = self.model._openerp_session.objects(self.model._openerp_model,
                                                  meth_name, *args)
        return res

    def get_complex_context(self, kwargs):
        context = kwargs.get('context', {})
        cnx = self.model._openerp_session.get_default_context().copy()
        if context is None:
            context = (self.oe_context or {}).copy()
        cnx.update(context)
        return cnx

    def execute_with_context(self, meth_name, *args, **kwargs):
        context = self.get_complex_context(kwargs)
        args += (context,)
        return self.execute(meth_name, *args)

    def oe_search(self, **kwargs):
        kw = self.query.as_oe_search()
        kw.update(kwargs)
        kw['context'] = self.get_complex_context(kw)
        logger.debug(u'Search kwargs: %r' % kw)
        return self.execute('search', kw['domain'],
                             kw['offset'],
                             kw['limit'] or None,
                             kw['order_by'],
                             kw['context'],
                             kw['count'])

    def oe_read(self, ids=None, fields=None, context=None, with_ids=False):
        if not fields:
            model_fields = self.model._meta.fields
            if not self.with_binary:
                model_fields = (f for f in model_fields if not \
                                isinstance(f, models.FileField))
            fields = [f.name for f in model_fields]
        if not ids:
            ids = self.oe_search()
        if fields == ('id',):
            # if need only ids 
            res = [ dict(id=i) for i in ids]
        else:
            res = self.execute_with_context('read', ids, fields,
                                            context=context)
        return (res, ids) if with_ids else res


    def oe_fields_view_get(self, view_id, view_type, context=None):
        return self.execute_with_context('fields_view_get',
                                         view_id, view_type, context=context)

    def oe_name_get(self, ids, context=None):
        return self.execute_with_context('name_get', ids, context=context)

    def oe_create(self, values, context=None):
        return self.execute_with_context('create', values, context=context)

    def oe_write(self, ids, values, context=None):
        return self.execute_with_context('write', ids, values, context=context)

    def oe_unlink(self, ids, context=None):
        return self.execute_with_context('unlink', ids, context=context)

    def oe_read_group(self, domain, fields, groupby, offset=0,
                      limit=None, context=None, orderby=False):
        return self.execute_with_context('read_group', domain, fields,
                                         groupby, offset, limit,context=context)

    def iterator(self):
        instances, ids = self.oe_read(with_ids=True)
        
        instances_dict = dict(((inst['id'], inst) for inst in instances))
        for _id in ids:
            inst = instances_dict.pop(_id)
            if inst is None:
                continue
            kwargs = openerp2django(inst, self.model)
            inst = self.model(**kwargs)
            inst.pk = inst.id
            yield inst

    def update(self, **kwargs):
        clone = self._clone()
        ids = clone.oe_search()
        return clone.oe_write(ids, django2openerp(kwargs))

    def delete(self):
        clone = self._clone()
        ids = clone.oe_search()
        return clone.oe_unlink(ids)

    def with_binary(self, flag=True):
        clone = self._clone()
        clone.with_binary = False
        return clone

    def values(self, *fields):
        return self._clone(klass=OpenERPValuesQuerySet, setup=True,
                           _fields=fields)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is "
                            "called with more than one field.")
        return self._clone(klass=OpenERPValuesListQuerySet, setup=True,
                           flat=flat,  _fields=fields)

    def get(self, **kwargs):
        clone = self.filter(**kwargs)
        objects = list(clone)
        num = len(objects)
        if num > 1:
            raise self.model.MultipleObjectsReturned('get() returned more than'\
            ' one %s -- ! Return %d Lookup parameters were %s'
                % (self.model._meta.object_name, num, kwargs))
        if num == 0:
            raise self.model.DoesNotExist("%s matching query does not exist."
                    % self.model._meta.object_name)
        return objects[0]

    def exists(self):
        if self._result_cache is None:
            return bool(self.oe_search(offset=0, limit=1))
        return bool(self._result_cache)

    def count(self):
        return self.oe_search(count=True)

    def context(self, context=None, **kwargs):
        clone = self._clone()
        if context is not None:
            clone.oe_context = context
        else:
            if clone.oe_context is None:
                clone.oe_context = {}
            clone.oe_context.update(kwargs)
        return clone

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(OpenERPQuerySet, self)._clone(klass, **kwargs)
        c.oe_context = self.oe_context.copy() if self.oe_context else None
        return c


class OpenERPValuesQuerySet(OpenERPQuerySet):

    def iterator(self):
        id_in_fields, fields = False, list(self._fields[:])
        if not 'id' in fields:
            fields.append('id')
            id_in_fields = True
        objs, ids = self.oe_read(fields=fields, with_ids=True)
        obj_dict = dict(((obj['id'], obj) for obj in objs))
        for _id in ids:
            row = obj_dict.pop(_id)
            if id_in_fields:
                del row['id']
            yield row

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(OpenERPValuesQuerySet, self)._clone(klass, **kwargs)
        if not hasattr(c, '_fields'):
            # Only clone self._fields if _fields wasn't passed into the cloning
            # call directly.
            c._fields = self._fields[:]
        return c


class OpenERPValuesListQuerySet(OpenERPValuesQuerySet):

    def iterator(self):
        for row in super(OpenERPValuesListQuerySet, self).iterator():
            row_vals = row.values()
            if self.flat and len(self._fields) == 1:
                yield row_vals[0]
            else:
                yield row_vals

    def _clone(self, *args, **kwargs):
        clone = super(OpenERPValuesListQuerySet, self)._clone(*args, **kwargs)
        if not hasattr(clone, "flat"):
            # Only assign flat if the clone didn't already get it from kwargs
            clone.flat = self.flat
        return clone
