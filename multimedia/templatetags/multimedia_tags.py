import string
from types import IntType, LongType, StringType, UnicodeType

from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, Library, loader, Node, Template, TemplateSyntaxError
from django.utils.translation import ugettext as _

from multimedia import settings
from multimedia.models import Media
from multimedia.utilities import parse_format
from tagging.models import Tag, TaggedItem
from tagging.utils import parse_tag_input


register = Library()


class ThumbnailNode(Node):
  def __init__(self, var_or_id, format=None, **extra):
    self.var_or_id = var_or_id
    self.format    = format
    self.extra     = extra

  def render(self, context):
    try:
      if self.var_or_id.isdigit():
        media = Media.objects.get(id=self.var_or_id)
      else:
        media = context[self.var_or_id]
    except ObjectDoesNotExist:
      return '<!-- failed to retrieve media with an id of "%d" -->' % self.var_or_id

    thumbnail = media.thumbnail(self.format)
    context = Context({'thumbnail':thumbnail, 'extra':self.extra, 'site':Site.objects.get_current()})
    return loader.render_to_string(thumbnail.format['template'], context)


class ThumbnailForMediaNode(Node):
  def __init__(self,var_or_id,format,context_var):
    self.var_or_id   = var_or_id
    self.format      = format
    self.context_var = context_var
    
  def render(self, context):
    if self.var_or_id.isdigit():
      media = Media.objects.get(id=self.var_or_id)
    else:
      media = context[self.var_or_id]
    thumbnail = media.thumbnail(self.format)
    context[self.context_var] = thumbnail
    return ''


class RecentMediaNode(Node):
  def __init__(self, count, context_var):
    self.count       = count
    self.context_var = context_var
    
  def render(self, context):
    context[self.context_var] = Media.objects.order_by('-imported')[:self.count]
    return ''
    
    
def do_thumbnail(parser, token):
  """
  Outputs an HTML <img> element to a media thumbnail, with an optional format
  string, otherwise, the 'default' format is used. Extra parameters are added
  to the <img> element; these can be used to set, e.g., an 'id' or 'class'.
  
  Usage::
  
    {% thumbnail [id|object] %}
    {% thumbnail [id|object] with format=400x400,square class=display:block; ... %}

  """
  bits = token.contents.split()
  len_bits = len(bits)
  if len_bits == 2:
    return ThumbnailNode(bits[1])
  elif len_bits >= 4:
    if bits[2] != 'with':
      raise TemplateSyntaxError(_("second argument to %s tag must be 'with'") % bits[0])
    kwargs = {}
    for i in range(3, len_bits):
      try:
        name, value = bits[i].split('=',1)
        kwargs[str(name)] = str(value)
      except ValueError:
        raise TemplateSyntaxError(_("%s tag was given a badly formatted option: '%s'") % (bits[0],bits[i]))
    return ThumbnailNode(bits[1],**kwargs)
  else:
    raise TemplateSyntaxError(_('%s tag requires either one or three or more arguments') % bits[0])


def do_thumbnail_for_media(parser,token):
  """
  Retrieves a thumbnail for a given Media object with a given format and stores it
  in a context variable.
  
  Usage::

    {% thumbnail_for_media [id|object] with format=[format] as [context_var] %}

    The thumbnail stored in 'context_var' has the following attributes:
      
      media     the Media instance of this thumbnail
      format    the format setting, as a dictionary
      url       the url to the thumbnail image
      width     the width of the thumbnail image
      height    the height of the thumbnail image
      
  """
  bits = token.contents.split()
  len_bits = len(bits)
  if len_bits == 6:
    if bits[2] != 'with':
      raise TemplateSyntaxError(_("second argument to %s tag must be 'with'") % bits[0])
    if bits[4] != 'as':
      raise TemplateSyntaxError(_("fourth argument to %s tag must be 'as'") % bits[0])
    if not bits[3].startswith('format='):
      raise TemplateSyntaxError(_("third argument to %s tag must start with 'format='") % bits[0])
    format = bits[3].split('=',1)[1]
    return ThumbnailForMediaNode(bits[1],format,bits[5])
  else:
    raise TemplateSyntaxError(_('%s tag requires six arguments') % bits[0])


def do_recent_media(parser,token):
  """
  Assigns recently imported media to a context variable.

  Usage::

    {% recent_media 10 as media_list %}

  """
  bits = token.contents.split()
  len_bits = len(bits)
  if len_bits == 4:
    if bits[2] != 'as':
      raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    if not bits[1].isdigit():
      raise TemplateSyntaxError(_("first argument to %s tag must be a positive integer") % bits[0])      
    count = int(bits[1])
    context_var = bits[3]
    return RecentMediaNode(count,context_var)
  else:
    raise TemplateSyntaxError(_('%s tag requires four arguments') % bits[0])


def thumbnail_url(media,format=None):
  return media.thumbnail(format).url


def render_multimedia_tags(s):
  t = Template("{% load multimedia_tags %}\n" + s)
  c = Context()
  return t.render(c)


register.tag('thumbnail', do_thumbnail)
register.tag('thumbnail_for_media', do_thumbnail_for_media)
register.tag('recent_media', do_recent_media)
register.filter(thumbnail_url)
register.filter(render_multimedia_tags)


# shorthand for rending all media tagged with X
#
#   {% render_media_tagged [tag,tag,tag] with format %}
#
# @register.inclusion_tag('multimedia/render_media_set.html')
# def render_media_tagged(tags):
#     try:        
#         objects = TaggedItem.objects.get_by_model(Media,tags)
#         set = 'random' + str(randrange(10000,99999))
#     except ObjectDoesNotExist:
#         objects = None
#         set = None
#     return {'objects':objects,'set':set}
