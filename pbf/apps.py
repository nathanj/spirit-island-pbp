from django.apps import AppConfig
import os


class PbfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pbf'

    def ready(self):
        if not os.environ.get('DOUBLE_ELEMENT_CARDS', ''):
            self.assert_no_double_element_cards()

    def assert_no_double_element_cards(self):
        # As of Nature Incarnate, there is no card published that has more than one of any element.
        # Therefore, to avoid any data entry error, we check for this and fail loudly if one is found.
        # If there were to be one in the future, either remove or modify this function.
        # Also see the environment variable setting DOUBLE_ELEMENT_CARDS that disables this check.

        from .models import Card
        for card in Card.objects.all():
            if not card.elements:
                continue
            elements = card.elements.split(',')
            if len(elements) != len(set(elements)):
                raise ValueError(f"card {card} has duplicate elements")
