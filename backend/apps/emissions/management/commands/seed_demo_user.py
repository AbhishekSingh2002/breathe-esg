from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a demo user for testing'

    def handle(self, *args, **options):
        username = 'analyst1'
        password = 'password123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            return
        
        User.objects.create_user(
            username=username,
            password=password
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created demo user: {username} / {password}')
        )
