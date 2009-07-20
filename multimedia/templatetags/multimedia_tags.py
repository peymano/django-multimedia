import re
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
  def __init__(self, var_or_id, context_var=None, format=None, **extra):
    self.var_or_id   = var_or_id
    self.context_var = context_var
    self.format      = format
    self.extra       = extra

  def render(self, context):
    try:
      if context.has_key(self.var_or_id):
        var_or_id = context[self.var_or_id]
      else:
        var_or_id = self.var_or_id

      if type(var_or_id) is int or var_or_id.isdigit():
        media = Media.objects.get(id=var_or_id)
      else:
        media = context[var_or_id]
    except ObjectDoesNotExist:
      return '<!-- failed to retrieve media with an id of "%d" -->' % var_or_id

    thumbnail = media.thumbnail(self.format)
    if thumbnail:
      if self.context_var:
        context[self.context_var] = thumbnail
        return ''
      else:
        context = Context({'thumbnail':thumbnail, 'extra':self.extra, 'site':Site.objects.get_current()})
        return loader.render_to_string(thumbnail.format['template'], context)
    else:
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
  Gets the thumbnail image for a given media object and either (1) renders the
  thumbnail using a given Django template or (2) assigns the thumbnail to a
  given context variable.

  Usage::

    To render a thumbnail using the default format:
    1. {% thumbnail [id|object] %}

    To render a thumbnail using the specified format:
    2. {% thumbnail [id|object] with format=400x400,square %}

    To render a thumbnail and pass extra context variables to the template:
    3. {% thumbnail [id|object] with format=400x400,square class=display:block; license=free ... %}

    The extra settings (in this case "class" and "license") are passed to the Django template as
    a context variable called 'extra'. The template would reference these as {{extra.class}} and
    {{exta.license}}, respectively.

    To assign the thumbnail to a context variable:
    4. {% thumbnail [id|object] with format=400x400,square class=display:block; as [context_var] %}

    The thumbnail stored in 'context_var' has the following attributes:

      media     the Media object for this thumbnail
      format    the format setting (as a dictionary)
      url       the url to the thumbnail image
      width     the width of the thumbnail image
      height    the height of the thumbnail image

  """
  bits = token.contents.split()
  len_bits = len(bits)
  if len_bits == 2:
    return ThumbnailNode(bits[1])
  elif len_bits >= 4:
    if bits[2] != 'with':
      raise TemplateSyntaxError(_("second argument to %s tag must be 'with'") % bits[0])
    if bits[-2] == 'as':
      args = bits[3:-2]
      context_var = bits[-1]
    else:
      args = bits[3:]
      context_var = None
    kwargs = {}
    for arg in args:
      try:
        name, value = arg.split('=',1)
        kwargs[str(name)] = str(value)
      except ValueError:
        raise TemplateSyntaxError(_("%s tag was given a badly formatted option: '%s'") % (bits[0],bits[i]))
    return ThumbnailNode(bits[1],context_var,**kwargs)
  else:
    raise TemplateSyntaxError(_('%s tag requires either one or 3+ arguments') % bits[0])


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
  thumbnail = media.thumbnail(format)
  if thumbnail:
    return thumbnail.url
  else:
    return None


def render_multimedia_tags(s):
  t = Template("{% load multimedia_tags %}\n" + s)
  c = Context()
  return t.render(c)


thumbnail_pattern = re.compile(r'{% thumbnail .+ %}',re.M)

def strip_multimedia_tags(s):
  return string.join(thumbnail_pattern.split(s))


register.tag('thumbnail', do_thumbnail)
register.tag('recent_media', do_recent_media)
register.filter(thumbnail_url)
register.filter(render_multimedia_tags)
register.filter(strip_multimedia_tags)


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
