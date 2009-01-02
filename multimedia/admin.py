from django.contrib import admin
from multimedia.models import Media


class MediaAdmin(admin.ModelAdmin):
  list_display = ('admin_img_tag','id','caption','imported','taken')
  list_filter = ('taken','imported')
  save_on_top = True
  search_fields = ('caption',)
  
  def admin_img_tag(self,media):
    return media.admin_thumbnail().as_img_tag()
  admin_img_tag.allow_tags = True


admin.site.register(Media,MediaAdmin)
