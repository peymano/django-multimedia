import os
import os.path
import re
from subprocess import Popen, PIPE
import string
import types

from PIL import Image, ImageFilter
from roundcorners import round_image
from multimedia import settings


dimension_re = re.compile(r'^(\d+)x(\d+)$',re.IGNORECASE)

def parse_format(format):
  "Format has the form '200x200,square,round=10,bg=ffffff'. All fields are optional."
  if type(format) is types.DictionaryType: # already parsed
    return format
  result = {}
  if format:
    for s in format.split(','):
      if '=' in s:
        name,value = s.split('=',1)
      else:
        name,value = (s,None)
      match = dimension_re.match(name)
      if match:
        result['dimensions'] = map(lambda s: int(s), match.groups())
      elif name == 'square':
        result['square'] = True
      elif name == '!square':
        result['square'] = False
      elif name == 'round':
        result['round'] = int(value)
      elif name == 'bg':
        result[name] = value.lower()
      elif name == 'template':
        result[name] = value
      elif name in settings.MULTIMEDIA_FORMATS.keys():
        f = parse_format(settings.MULTIMEDIA_FORMATS[name])
        if f:
          result.update(f)
        else:
          raise ValueError('Bad format expression in MULTIMEDIA_FORMATS["%s"]' % name)
      else:
        raise ValueError('Unknown thumbnail format name or setting:',name)
  return result


def compute_format(first,second=None,third=None):
  result = parse_format(first)
  result.update( parse_format(second) )
  result.update( parse_format(third)  )
  return result


def compute_square_crop(dimensions):
  width, height = dimensions
  if width > height:
    diff = (width - height)/2
    crop = (diff, 0, width-diff, height)
  else:
    diff = (height - width)/2
    crop = (0, diff, width, height-diff)
  return crop


def make_thumbnail(src,format,dst):
  image = Image.open(src)
  # square
  if format['square']:
    crop = compute_square_crop(image.size)
    image = image.crop(crop)
  # dimensions
  image.thumbnail(format['dimensions'], Image.ANTIALIAS)
  # round
  if format['round']:
    image = round_image(image,radius=format['round'],bg_color='#'+format['bg']);
  # save
  image.save(dst)


def compute_thumbnail_dimensions(src,format):
  width, height = src
  # square
  if format['square']:
    crop = compute_square_crop(src)
    width, height = crop[2]-crop[0], crop[3]-crop[1]
  # dimensions
  x_factor = float(width)  / format['dimensions'][0]
  y_factor = float(height) / format['dimensions'][1]
  if x_factor > y_factor:
    if x_factor > 1:
      width, height = format['dimensions'][0], int(height / x_factor)
  else:
    if y_factor > 1:
      width, height = int(width / y_factor), format['dimensions'][1]
  return width, height
  
  
def update_media(media):
  filepath = media.mediafile.path
  _, ext = os.path.splitext(filepath)
  if ext.lower() in ['.gif','.jpg','.jpeg','.png','tif','tiff']:
    # extract metadata
    metadata = extract_exif(filepath)
    # get dimensions
    image = Image.open(filepath)
    width,height = image.size
    # resize file
    if settings.MULTIMEDIA_MAX_DIMENSIONS:
      if width  > settings.MULTIMEDIA_MAX_DIMENSIONS[0] or \
         height > settings.MULTIMEDIA_MAX_DIMENSIONS[1]:
        image.thumbnail(settings.MULTIMEDIA_MAX_DIMENSIONS, Image.ANTIALIAS)
        image.save(filepath)
    # update fields
    media.kind        = 'i'
    media.width       = width
    media.height      = height
    media.taken       = parse_date(metadata.get('DateTimeOriginal',None))
    media.metadata    = string.join(map(lambda i: i[0]+': '+i[1], metadata.items()),'\n')


def parse_date(s):
  from datetime import datetime
  from time import strptime
  if s:
    try:
      return datetime(*strptime('2008:12:27 13:00:04',"%Y:%m:%d %H:%M:%S")[:5])
    except ValueError:
      return None
  else:
    return None


def extract_exif(filepath):
  # execute "exiftool -s -t [set of tags] [filepath]" and parse the output
  tags = ['Make','Model','DateTimeOriginal','FocalLength','ShutterSpeed','Aperture','ISO','Flash']
  tag_args = "-" + string.join(tags," -")
  cmd = "exiftool -s -t %s %s" % (tag_args,filepath)
  p = Popen(cmd, shell=True, stdout=PIPE)
  lines = p.communicate()[0].strip().split('\n')
  result = {}
  for l in lines:
    if l:
      tag,value = l.split('\t')
      result[tag] = value
  return result
