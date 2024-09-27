from django.apps import AppConfig


class PbfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pbf'

    def ready(self):
        self.assert_no_double_element_cards()

    def assert_no_double_element_cards(self):
        # As of Nature Incarnate, there is no card published that has more than one of any element.
        # Therefore, to avoid any data entry error, we check for this and fail loudly if one is found.
        # If there were to be one in the future, either remove or modify this function.
        # Also be sure to change get_elements in the Card model.

        from .models import Card
        for card in Card.objects.all():
            if not card.elements:
                continue
            elements = card.elements.split(',')
            if len(elements) != len(set(elements)):
                raise ValueError(f"card {card} has duplicate elements")
