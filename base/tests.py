import unittest
from django.db.models import Q
from djoe.base.models import OpenERPModelFactory

OpenCountry = OpenERPModelFactory('res.country').get_model()
OpenState = OpenERPModelFactory('res.country.state').get_model()


class LookUpTestCase(unittest.TestCase):

    def test_lookup(self):
        qs = OpenState.objects.filter(id__in=[1, 3, 15])
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('id', 'in', [1, 3, 15])])

        qs = OpenState.objects.filter(name__contains='asd')
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('name', 'like', 'asd')])

        qs = OpenState.objects.filter(name__icontains='asd')
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('name', 'ilike', 'asd')])

        qs = OpenState.objects.filter(id__gt=15)
        self.assertEqual(qs.query.as_oe_search()['domain'], [('id', '>', 15)])

        qs = OpenState.objects.filter(id__lt=34)
        self.assertEqual(qs.query.as_oe_search()['domain'], [('id', '<', 34)])

        qs = OpenState.objects.filter(id__gte=15)
        self.assertEqual(qs.query.as_oe_search()['domain'], [('id', '>=', 15)])

        qs = OpenState.objects.filter(id__lte=34)
        self.assertEqual(qs.query.as_oe_search()['domain'], [('id', '<=', 34)])

        qs = OpenState.objects.filter(id__range=[2, 20])
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&', ('id', '>=', 2), ('id', '<=', 20)])

    def test_isnull(self):
        qs = OpenState.objects.filter(id__isnull=True)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('id', '=', False)])
        qs = OpenState.objects.filter(country_id__id__isnull=True)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('country_id.id', '=', False)])

        qs = OpenState.objects.filter(id__isnull=False)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['!', ('id', '=', False)])
        qs = OpenState.objects.filter(country_id__id__isnull=False)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['!', ('country_id.id', '=', False)])

    def test_long_lookup(self):
        qs = OpenState.objects.filter(country_id__name='asd')
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('country_id.name', '=', 'asd')])
        qs = OpenState.objects.filter(country_id__id__in=(1, 3, 5))
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('country_id.id', 'in', (1, 3, 5))])


class FilterTestCase(unittest.TestCase):

    def test_simple(self):
        qs = OpenState.objects.filter(id=35)
        self.assertEqual(qs.query.as_oe_search()['domain'], [('id', '=', 35)])

        qs = OpenState.objects.filter(name='asd')
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         [('name', '=', 'asd')])

    def test_two(self):
        qs = OpenState.objects.filter(id__gt=1, country_id__pk__lt=100)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&', ('id', '>', 1), ('country_id.id', '<', 100)])

    def test_three(self):
        qs = OpenState.objects.filter(id__gt=1, country_id__pk__lt=100)
        qs = qs.filter(id__lt=300)
        list(qs)

        self.assertEqual(qs.query.as_oe_search()['domain'],
                        ['&', ('id', '>', 1), '&', ('country_id.id', '<', 100),
                         ('id', '<', 300)])

    def test_foure(self):
        qs = OpenState.objects.filter(id__gt=1, country_id__pk__lt=100)
        qs = qs.filter(id__lt=300)
        qs = qs.filter(name__icontains='a')
        list(qs)

        self.assertEqual(qs.query.as_oe_search()['domain'],
                        ['&', ('id', '>', 1), '&', ('country_id.id', '<', 100),
                         '&', ('id', '<', 300), ('name', 'ilike', 'a')])

    def test_exclude(self):
        qs = OpenState.objects.exclude(id__in=[1, 3, 15])
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['!', ('id', 'in', [1, 3, 15])])

        qs = OpenState.objects.exclude(name__contains='asd')
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['!', ('name', 'like', 'asd')])

    def test_complex(self):
        qs = OpenState.objects.filter(id__in=[1, 3, 15], id__gt=5)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&', ('id', 'in', [1, 3, 15]), ('id', '>', 5)])

        qs = OpenState.objects.filter(name='asd', id__in=[1, 3, 15])
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&', ('name', '=', 'asd'),
                                                ('id', 'in', [1, 3, 15])])

    def test_complex1(self):
        qs = OpenState.objects.filter(id__range=(15, 30))
        qs = qs.exclude(id__lt=20)
        qs = qs.exclude(id__in=(28, 29))
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&', ('id', '>=', 15), '&', ('id', '<=', 30),
                          '&',
                          '!', ('id', '<', 20), '!', ('id', 'in', (28, 29))])

    def test_complex2(self):
        qs = OpenState.objects.filter(id__range=(15, 30),
                                      country_id__pk__gt=1)
        qs = qs.exclude(id__lt=20)
        qs = qs.exclude(id__in=(28, 29))
        list(qs)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['&',('id', '>=', 15), '&', ('id', '<=', 30),
                          '&',('country_id.id', '>', 1),
                          '&',
                          '!', ('id', '<', 20), '!', ('id', 'in', (28, 29))])


class QObjectTestCase(unittest.TestCase):

    def test_two(self):
        q1 = Q(id__lt=20)
        q2 = Q(id__gt=40)
        qs = OpenState.objects.filter(q1 | q2)
        list(qs)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['|', ('id', '<', 20), ('id', '>', 40)])


    def test_three(self):
        q1 = Q(id__lt=20)
        q2 = Q(id__gt=40)
        q3 = Q(id=5)
        qs = OpenState.objects.filter(q1 | q2 | q3)
        list(qs)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['|', ('id', '<', 20), '|', ('id', '>', 40),
                          ('id', '=', 5), ])

    def test_with_range(self):
        q1 = Q(id__lt=20)
        q2 = Q(id__range=[5,15])
        qs = OpenState.objects.filter(q1 | q2)
        list(qs)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['|', ('id', '<', 20), '&', ('id', '>=', 5),
                          ('id', '<=', 15)])

    def test_with_and(self):
        q1 = Q(id__lt=20)
        q2 = Q(id__gt=40)
        qs = OpenState.objects.filter(q1 | q2, company_id__lt=280)
        list(qs)
        self.assertEqual(qs.query.as_oe_search()['domain'],
                         ['|', ('id', '<', 20), ('id', '>', 40),
                          '&', ('company_id.id', '<', 280)])


class OrderByTestCase(unittest.TestCase):

    def test_simple(self):
        qs = OpenState.objects.filter().order_by('name')
        self.assertEqual(qs.query.as_oe_search()['order_by'], 'name')

        qs = OpenState.objects.filter().order_by('-name')
        self.assertEqual(qs.query.as_oe_search()['order_by'], 'name desc')

        qs = OpenState.objects.filter().order_by('name', '-id')
        self.assertEqual(qs.query.as_oe_search()['order_by'], 'name, id desc')


class LimitsTestCase(unittest.TestCase):

    def test_simple(self):
        qs = OpenState.objects.filter()
        search = qs.query.as_oe_search()
        self.assertEqual(search['offset'], 0)
        self.assertEqual(search['limit'], None)

        qs = OpenState.objects.filter()[:110]
        search = qs.query.as_oe_search()
        self.assertEqual(search['offset'], 0)
        self.assertEqual(search['limit'], 110)

        qs = OpenState.objects.filter()[15:110]
        search = qs.query.as_oe_search()
        self.assertEqual(search['offset'], 15)
        self.assertEqual(search['limit'], 95)

