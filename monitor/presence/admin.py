from django.contrib import admin
from presence.models import Person, Activity

class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid')
    search_fields = ('name', 'uuid')

class ActivityAdmin(admin.ModelAdmin):
    search_fields = ('person__name', 'person__uuid')
    list_filter = ('first_seen', 'last_seen')
    list_display = ('person_name', 'first_seen', 'last_seen', 'seen_for')
    ordering = ('-first_seen',)

    def person_name(self, obj):
        return obj.person.name

admin.site.register(Person, PersonAdmin)
admin.site.register(Activity, ActivityAdmin)
