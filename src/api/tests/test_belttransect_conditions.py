from django.test import TestCase

from api.models import BeltTransectWidth, BeltTransectWidthCondition


class BeltTransectWidthNoGapsTest(TestCase):
    """
    val <= 10
    val > 10
    """

    def setUp(self):
        self.belt_transect_width = BeltTransectWidth.objects.create(name="Test BTW")

        self.btw_cond_lte_10 = BeltTransectWidthCondition.objects.create(
            belttransectwidth=self.belt_transect_width,
            operator=BeltTransectWidthCondition.OPERATOR_LTE,
            size=10,
            val=1,
        )

        self.btw_cond_gt_10 = BeltTransectWidthCondition.objects.create(
            belttransectwidth=self.belt_transect_width,
            operator=BeltTransectWidthCondition.OPERATOR_GT,
            size=10,
            val=2,
        )

    def tearDown(self):
        self.btw_cond_lte_10.delete()
        self.btw_cond_gt_10.delete()
        self.belt_transect_width.delete()

        self.belt_transect_width = None
        self.btw_cond_lte_10 = None
        self.btw_cond_gt_10 = None

    def test_no_range_gap(self):
        condition = self.belt_transect_width.get_condition(3)
        assert condition.val == 1

        condition = self.belt_transect_width.get_condition(10)
        assert condition.val == 1

        condition = self.belt_transect_width.get_condition(12)
        assert condition.val == 2

        condition = self.belt_transect_width.get_condition(-1)
        assert condition is None

        condition = self.belt_transect_width.get_condition(None)
        assert condition is None


class BeltTransectWidthGapsTest(TestCase):
    """
    val <= 8
    val > 10
    """

    def setUp(self):
        self.belt_transect_width = BeltTransectWidth.objects.create(name="Test BTW")

        self.btw_cond_lte_8 = BeltTransectWidthCondition.objects.create(
            belttransectwidth=self.belt_transect_width,
            operator=BeltTransectWidthCondition.OPERATOR_LTE,
            size=8,
            val=1,
        )

        self.btw_cond_gt_10 = BeltTransectWidthCondition.objects.create(
            belttransectwidth=self.belt_transect_width,
            operator=BeltTransectWidthCondition.OPERATOR_GT,
            size=10,
            val=2,
        )

        self.btw_cond_default = BeltTransectWidthCondition.objects.create(
            belttransectwidth=self.belt_transect_width,
            val=3,
        )

    def tearDown(self):
        self.btw_cond_lte_8.delete()
        self.btw_cond_gt_10.delete()
        self.btw_cond_default.delete()
        self.belt_transect_width.delete()

        self.belt_transect_width = None
        self.btw_cond_lte_8 = None
        self.btw_cond_gt_10 = None
        self.btw_cond_default = None

    def test_range_gap(self):
        condition = self.belt_transect_width.get_condition(3)
        assert condition.val == 1

        condition = self.belt_transect_width.get_condition(10)
        assert condition.val == 3

        condition = self.belt_transect_width.get_condition(12)
        assert condition.val == 2

        condition = self.belt_transect_width.get_condition(-1)
        assert condition is None

        condition = self.belt_transect_width.get_condition(None)
        assert condition is None
