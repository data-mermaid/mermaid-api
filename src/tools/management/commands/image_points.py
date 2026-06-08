from django.core.management.base import BaseCommand
from PIL import Image as PILImage, ImageDraw

from api.models import Image
from api.utils import classification


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
            self.stderr.write(f"Image with id {image} does not exist.")
            self.exit(1)

        points = classification.generate_points(img_rec, 25)

        with img_rec.image.open("rb") as f:
            pil_image = PILImage.open(f).copy()

        draw = ImageDraw.Draw(pil_image)
        for point in points:
            draw.rectangle(
                (
                    point[1] - 122,
                    point[0] - 122,
                    point[1] + 122,
                    point[0] + 122,
                ),
                outline="red",
                width=5,
            )
            draw.circle((point[1], point[0]), radius=10, fill="red")

        pil_image.save(output_image)
