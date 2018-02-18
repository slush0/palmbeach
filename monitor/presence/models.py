from django.db import models

class Person(models.Model):
    uuid = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=32)

    def __str__(self):
        return '%s (%s)' % (self.name, self.uuid)

class Activity(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    counter = models.IntegerField()
    first_seen = models.DateTimeField(db_index=True)
    last_seen = models.DateTimeField()
    seen_for = models.DurationField()
    rssi = models.CharField(max_length=40, blank=True) # 10 values semicolon-delimited

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'

    def __str__(self):
        return "%s: %s (%s)" % (self.person.name, self.first_seen.date(), self.seen_for)
