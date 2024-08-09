from PIL import ImageDraw, Image as PILImage
from django.core.management.base import BaseCommand

from api.utils import classification
from api.models import Image


class Command(BaseCommand):
    help = """
    Add classification points to image.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "image",
            help="Image record id.",
        )
        
        parser.add_argument(
            "output_image",
            help="Output file path",
        )

    def handle(self, image, output_image, **options):
        img_rec = Image.objects.get_or_none(id=image)
        if img_rec is None:
            self.stderr.write("Image does not exist")
            self.exit(1)
        
        points = classification.generate_points(img_rec, 25)
        pil_image = PILImage.open(img_rec.image)
        draw = ImageDraw.Draw(pil_image)
        for point in points:
            draw.rectangle(
                (
                    point[1] - 122, point[0] - 122,
                    point[1] + 122, point[0] + 122,
                ),
                outline="red",
                width=5
            )
            draw.circle(
                (point[1], point[0]),
                radius=10,
                fill="red"
            )

        pil_image.save(output_image)
