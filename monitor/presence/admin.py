from django.contrib import admin
from presence.models import Person, Activity

class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid')
    search_fields = ('name', 'uuid')

class ActivityAdmin(admin.ModelAdmin):
    search_fields = ('person__name', 'person__uuid')

admin.site.register(Person, PersonAdmin)
admin.site.register(Activity, ActivityAdmin)
