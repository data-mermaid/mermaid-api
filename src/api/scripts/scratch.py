from api.models import BeltFishSESQLModel
from api.utils.timer import timing


@timing
def run():
    for r in BeltFishSESQLModel.objects.all().sql_table(project_id="2c56b92b-ba1c-491f-8b62-23b1dc728890"):
        print(r)
