from django.conf import settings

def djoe(request):
    print '^^'*300
    print settings.DJOE_CLIENT_OPTIONS
    return {'DJOE': settings.DJOE_CLIENT_OPTIONS}
