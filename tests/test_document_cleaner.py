import unittest

from backend.services.document_cleaner import DocumentCleaner


class DocumentCleanerTests(unittest.TestCase):
    def setUp(self):
        self.cleaner = DocumentCleaner()

    def test_normalizes_unicode_whitespace_and_punctuation(self):
        value = "\ufeffＡＢＣ\u200b  测试！！！\r\n\r\n\r\n下一行"
        self.assertEqual(self.cleaner.normalize_text(value), "ABC 测试!\n\n下一行")

    def test_removes_repeated_page_noise_and_page_numbers(self):
        chunks = [
            {"content": f"企业内部资料\n第 {page} 页\n第{page}章有效内容。\n保密文件", "metadata": {"page": page}}
            for page in range(1, 4)
        ]
        result = self.cleaner.clean("\n".join(item["content"] for item in chunks), chunks)
        joined = "\n".join(item["content"] for item in result.chunks)
        self.assertNotIn("企业内部资料", joined)
        self.assertNotIn("保密文件", joined)
        self.assertNotIn("第 1 页", joined)
        self.assertIn("第1章有效内容。", joined)
        self.assertGreaterEqual(result.report["removed_noise_lines"], 9)

    def test_removes_exact_duplicate_chunks(self):
        chunks = [
            {"content": "员工请假需要提前提交申请。", "metadata": {}},
            {"content": "员工请假需要提前提交申请。", "metadata": {}},
        ]
        result = self.cleaner.clean("员工请假需要提前提交申请。", chunks)
        self.assertEqual(len(result.chunks), 1)
        self.assertEqual(result.report["duplicate_chunks"], 1)
        self.assertEqual(result.chunks[0]["metadata"]["cleaner_version"], "1.0")

    def test_filters_low_quality_ocr_line(self):
        chunks = [{"content": "正常的业务说明文字。\n@@@###$$$%%%^^^", "metadata": {}}]
        result = self.cleaner.clean(chunks[0]["content"], chunks)
        self.assertNotIn("@@@", result.chunks[0]["content"])
        self.assertEqual(result.report["removed_ocr_lines"], 1)

    def test_preserves_and_labels_excel_rows(self):
        chunks = [{"content": "姓名 | 部门\n张三 | 人力资源部", "metadata": {"sheet": "员工"}}]
        result = self.cleaner.clean(chunks[0]["content"], chunks)
        self.assertTrue(result.chunks[0]["content"].startswith("【工作表: 员工】"))
        self.assertEqual(result.chunks[0]["metadata"]["table_row_count"], 2)
        self.assertEqual(result.report["table_rows"], 2)


if __name__ == "__main__":
    unittest.main()