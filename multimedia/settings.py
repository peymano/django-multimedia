"""
Custom settings for django-multimedia app.
"""

from django.conf import settings

MULTIMEDIA_FORMATS = {
  # default template, inherited by all templates
  'default': '200x200,!square,round=10,bg=ffffff,template=render-media-default.html',
  
  # admin template is used by the Django admin UI (template setting is ignored)
  'admin'  : '100x100,square,round=10,bg=ffffff',
}
MULTIMEDIA_FORMATS.update( getattr(settings,'MULTIMEDIA_FORMATS',{}) )

MULTIMEDIA_PATH = \
  getattr(settings,'MULTIMEDIA_PATH','content/multimedia/%Y/%m/%d')

MULTIMEDIA_MAX_DIMENSIONS = \
  getattr(settings,'MULTIMEDIA_MAX_DIMENSIONS',None)
