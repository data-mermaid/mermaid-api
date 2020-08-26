from datetime import datetime
from django.test import TestCase
from api.resources.mixins import UpdatesMixin


class UpdatesMixinTestCase(TestCase):
    def test_compress(self):
        added = [
            [
                datetime(2019, 1, 1, 1, 0, 0),
                dict(id=1, updated_on=str(datetime(2019, 1, 1, 1, 0, 0))),
            ],
            [
                datetime(2019, 1, 1, 1, 1, 0),
                dict(id=2, updated_on=str(datetime(2019, 1, 1, 1, 1, 0))),
            ],
            [
                datetime(2019, 1, 1, 1, 1, 1),
                dict(id=10, updated_on=str(datetime(2019, 1, 1, 1, 1, 1))),
            ],  # Removed
            [
                datetime(2019, 1, 1, 1, 1, 1),
                dict(id=11, updated_on=str(datetime(2019, 1, 1, 1, 1, 1))),
            ],  # Removed
            [
                datetime(2019, 1, 1, 1, 1, 1),
                dict(id=12, updated_on=str(datetime(2019, 1, 1, 1, 1, 1))),
            ],
        ]

        modified = [
            [
                datetime(2019, 1, 1, 1, 1, 5),
                dict(id=2, updated_on=str(datetime(2019, 1, 1, 1, 1, 5))),
            ],  # Removed
            [
                datetime(2019, 1, 1, 1, 1, 5),
                dict(id=3, updated_on=str(datetime(2019, 1, 1, 1, 1, 5))),
            ],
            [
                datetime(2019, 1, 1, 1, 2, 0),
                dict(id=5, updated_on=str(datetime(2019, 1, 1, 1, 2, 0))),
            ],
        ]

        deleted = [
            [
                datetime(2019, 1, 1, 1, 1, 5),
                dict(id=4, timestamp=datetime(2019, 1, 1, 1, 1, 5)),
            ],
            [
                datetime(2019, 1, 1, 1, 1, 0),
                dict(id=5, timestamp=datetime(2019, 1, 1, 1, 1, 0)),
            ],  # Removed
            [
                datetime(2019, 1, 1, 1, 1, 1),
                dict(id=10, timestamp=datetime(2019, 1, 1, 1, 1, 1)),
            ],
            [
                datetime(2019, 1, 1, 1, 1, 2),
                dict(id=11, timestamp=datetime(2019, 1, 1, 1, 1, 2)),
            ],
            [
                datetime(2019, 1, 1, 1, 1, 0),
                dict(id=12, timestamp=datetime(2019, 1, 1, 1, 1, 0)),
            ],  # Removed
        ]

        mixin = UpdatesMixin()
        a, m, d = mixin.compress(added, modified, deleted)

        assert len(a) == 3
        assert len(m) == 2
        assert len(d) == 3

        assert sorted([rec["id"] for rec in a]) == [1, 2, 12]
        assert sorted([rec["id"] for rec in m]) == [3, 5]
        assert sorted([rec["id"] for rec in d]) == [4, 10, 11]
