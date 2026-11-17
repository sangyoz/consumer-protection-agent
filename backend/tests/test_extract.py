"""Extraction regressions: preserve source spans and avoid unnamed merchants."""
import unittest
from app.services.extract import extract

CASES = [
    ('我在淘宝一家耳机店买了一副299元的蓝牙耳机，收到当天发现右耳没有声音。我保留了订单、付款截图和故障视频，还没有联系商家，希望退货退款。', '蓝牙耳机', None),
    ('我买了299元的一副蓝牙耳机，右耳没声音。', '蓝牙耳机', None),
    ('我买了一副蓝牙耳机299元，无法使用。', '蓝牙耳机', None),
    ('我在淘宝小米官方旗舰店买了个蓝牙耳机，花了299元。', '蓝牙耳机', '小米官方旗舰店'),
    ('我在京东某家数码店买了一台2999元的电脑。', '电脑', None),
    ('我在线下健身房购买了3000元的30次私教课，已经上了8次。', '私教课', None),
    ('我在星光数码店买了蓝牙耳机，无法使用。', '蓝牙耳机', '星光数码店'),
]

class ExtractionTests(unittest.TestCase):
    def test_product_and_merchant_boundaries(self):
        for text, product, merchant in CASES:
            with self.subTest(text=text):
                result = extract(text)
                self.assertEqual(result['fields'].get('product'), product)
                self.assertEqual(result['fields'].get('merchant'), merchant)
                for row in result['evidence']:
                    self.assertEqual(text[row['start']:row['end']], row['snippet'])
                if merchant is None:
                    self.assertIn('merchant', [row['field'] for row in result['missing']])

    def test_original_report_keeps_correct_amount_platform_and_goal(self):
        fields = extract(CASES[0][0])['fields']
        self.assertEqual(fields['amount'], 299)
        self.assertEqual(fields['platform'], '淘宝')
        self.assertEqual(fields['goal'], '退货退款')
