"""Offline checks for TXT conversion; fixtures are synthetic, not legal sources."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.convert_laws import article_number, convert, read_text, split_articles


class LawConversionTests(unittest.TestCase):
    def test_chinese_number_and_wrapped_reporting_prefix(self):
        self.assertEqual(article_number('一千二百六十'), '1260')
        rows, _ = split_articles(
            '《测试法》第一条规定，第一款。\n第二款引用本法第二条。\n'
            '《测试法》第二条规定：另一条。\n', '测试法', '测试法.txt')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['content'], '第一条 第一款。\n第二款引用本法第二条。')
        self.assertEqual(rows[1]['article'], '2')

    def test_section_heading_and_indented_paragraphs(self):
        rows, warnings = split_articles(
            '第一章 总则\n第一条 内容一。\n  （一）子项。\n第二章 责任\n第二条 内容二。\n',
            '测试法', '测试法.txt')
        self.assertNotIn('第二章', rows[0]['content'])
        self.assertIn('（一）子项', rows[0]['content'])
        self.assertTrue(warnings)

    def test_duplicate_and_inserted_article_fail_without_silent_merge(self):
        for text in ('第一条 原文。\n第一条 重复。\n', '第一条 原文。\n第二条之一 新增。\n'):
            with self.assertRaises(ValueError):
                split_articles(text, '测试法', '测试法.txt')

    def test_draft_then_ready_metadata_and_raw_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'raw'
            raw.mkdir()
            path = raw / '测试法.txt'
            original = '第一条 测试内容。\n第二条 第二款内容。\n'.encode('utf-8')
            path.write_bytes(original)
            kwargs = dict(input_dir=raw, output=root / 'draft.jsonl', ready_output=root / 'laws.jsonl',
                          metadata_path=root / 'metadata.json', report_path=root / 'report.json')
            first = convert(**kwargs)
            self.assertEqual(first['total_articles'], 2)
            self.assertFalse(first['ready'])
            self.assertFalse(kwargs['ready_output'].exists())
            metadata = json.loads(kwargs['metadata_path'].read_text(encoding='utf-8'))
            metadata[path.name].update(source='https://flk.npc.gov.cn/test-only',
                                       effective_from='2020-01-01', reviewed_at='2025-01-01')
            kwargs['metadata_path'].write_text(json.dumps(metadata), encoding='utf-8')
            second = convert(**kwargs)
            self.assertTrue(second['ready_output_updated'])
            records = [json.loads(line) for line in kwargs['ready_output'].read_text(encoding='utf-8').splitlines()]
            self.assertEqual([row['article'] for row in records], ['1', '2'])
            self.assertNotEqual(records[0]['id'], records[1]['id'])
            self.assertEqual(path.read_bytes(), original)
            previous_ready = kwargs['ready_output'].read_bytes()
            metadata[path.name]['reviewed_at'] = ''
            kwargs['metadata_path'].write_text(json.dumps(metadata), encoding='utf-8')
            self.assertFalse(convert(**kwargs)['ready_output_updated'])
            self.assertEqual(kwargs['ready_output'].read_bytes(), previous_ready)

    def test_utf16_bom_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '法.txt'
            path.write_bytes('第一条 内容。'.encode('utf-16'))
            text, encoding = read_text(path)
            self.assertEqual(encoding, 'utf-16')
            self.assertEqual(text, '第一条 内容。')


if __name__ == '__main__':
    unittest.main()
