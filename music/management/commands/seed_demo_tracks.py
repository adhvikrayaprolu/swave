from django.core.management.base import BaseCommand
from music.models import Track

class Command(BaseCommand):
    help = 'Seed a deterministic offline metadata catalog; no external API calls.'
    def handle(self, *args, **options):
        for i, (title, artist) in enumerate([('Morning Light','Demo Ensemble'),('Night Walk','Demo Quartet'),('Open Water','Demo Studio'),('Quiet City','Demo Collective')], 1):
            Track.objects.get_or_create(external_id=f'demo-{i}', defaults={
                'title':title, 'artist':artist, 'source':'demo', 'provider':'demo', 'provider_track_id':f'demo-{i}'})
        self.stdout.write(self.style.SUCCESS('Demo catalog ready (metadata only; previews optional).'))
