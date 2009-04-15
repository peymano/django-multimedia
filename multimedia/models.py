import os
import os.path
from datetime import datetime

from django.conf import settings as djangosettings
from django.db import models
from PIL import Image, ImageFilter
from tagging.fields import TagField

from multimedia import settings
from multimedia.utilities import compute_format,compute_thumbnail_dimensions,make_thumbnail,update_media


MEDIA_KIND = (
  ('a', 'Audio'),
  ('i', 'Image'),
  ('m', 'Movie'),
)


class Media(models.Model):
  mediafile = models.FileField(upload_to=settings.MULTIMEDIA_PATH,max_length=256,blank=False)
  kind = models.CharField(max_length=1,choices=MEDIA_KIND,blank=True)
  caption = models.TextField(blank=True)
  tags = TagField()
  attribution_name = models.CharField(max_length=128,blank=True)
  attribution_url = models.URLField(verify_exists=False,max_length=1024,blank=True)
  taken = models.DateTimeField('Date taken',blank=True,null=True)
  imported = models.DateTimeField('Date imported',default=datetime.now)
  width = models.PositiveIntegerField(default=0)
  height = models.PositiveIntegerField(default=0)
  metadata = models.TextField(blank=True,null=True)

  class Meta:
    verbose_name_plural = 'media'
    ordering = ('-imported',)
    get_latest_by = ('imported',)

  def __unicode__(self):
    return (self.caption or '(no caption)') + ' (id:%d)' % self.id
  
  def save(self):
    try:
      update_media(self)
    finally:
      super(Media, self).save()
    
  def delete(self):
    try:
      from glob import glob
      pattern = os.path.join(djangosettings.MEDIA_ROOT,self.thumbnail_glob())
      for f in glob(pattern):
        os.remove(f)
    finally:
      super(Media, self).delete()
    
  def get_media_url(self):
    return self.mediafile.url
    
  def admin_thumbnail(self):
    return self.thumbnail(settings.MULTIMEDIA_FORMATS['admin'])

  def thumbnail(self,format=None):
    f = compute_format(settings.MULTIMEDIA_FORMATS['default'],format)
    name = self.create_thumbnail(f)
    if name:
      url = os.path.join(djangosettings.MEDIA_URL,name)
      width, height = compute_thumbnail_dimensions((self.width,self.height), f)
      return Thumbnail(self,f,url,width,height)
    else:
      return None

  def thumbnail_name(self,format):
    # like self.mediafile.name except that the filename is replaced with
    # a string of the form "tn-<basename>-200x200-sq-rd10-bgff0000.<ext>"
    head, tail = os.path.split(self.mediafile.name)
    basename, ext = os.path.splitext(tail)
    width, height = format['dimensions']
    s = 'tn-%s-%sx%s' % (basename,width,height)
    if format['square']:
      s += "-sq"
    if format['round'] != 0:
      s += "-rd" + str(format['round'])
    if format['bg'] != 'ffffff':
      s += '-bg' + format['bg']
    s += ext.lower()
    return os.path.join(head,s)
    
  def thumbnail_glob(self):
    head, tail = os.path.split(self.mediafile.name)
    basename, ext = os.path.splitext(tail)
    s = 'tn-%s-*%s' % (basename,ext.lower())
    return os.path.join(head,s)

  def create_thumbnail(self,format):
    if self.kind == 'i':
      name = self.thumbnail_name(format)
      filepath = os.path.join(djangosettings.MEDIA_ROOT,name)
      if not os.path.isfile(filepath):
        make_thumbnail(self.mediafile.path,format,filepath)
      return name
    else:
      return None


class Thumbnail(object):
  def __init__(self,media,format,url,width,height):
    self.media  = media
    self.format = format
    self.url    = url
    self.width  = width
    self.height = height

  def as_img_tag(self):
    return '<img src="%s" width="%d" height="%d"/>' % (self.url, self.width, self.height)
  as_img_tag.allow_tags = True

