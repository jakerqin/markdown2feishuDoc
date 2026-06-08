import unittest

from src import feishu_client


class DummyRaw:
    content = b'{"error":"folder token invalid"}'


class DummyResponse:
    code = 99991663
    msg = "permission denied"
    raw = DummyRaw()


class FeishuClientErrorFormattingTests(unittest.TestCase):
    def test_format_response_error_includes_sdk_details(self):
        self.assertTrue(hasattr(feishu_client, "format_response_error"))
        message = feishu_client.format_response_error("创建文件夹失败", DummyResponse())

        self.assertIn("创建文件夹失败", message)
        self.assertIn("code=99991663", message)
        self.assertIn("msg=permission denied", message)
        self.assertIn("folder token invalid", message)

    def test_delete_old_document_not_found_is_handled_as_idempotent(self):
        class _Resp:
            def __init__(self, code):
                self.code = code

        self.assertTrue(feishu_client.FeishuClient._is_old_doc_not_found(_Resp(1061003)))
        self.assertFalse(feishu_client.FeishuClient._is_old_doc_not_found(_Resp(0)))
        self.assertFalse(feishu_client.FeishuClient._is_old_doc_not_found(_Resp(500)))


if __name__ == "__main__":
    unittest.main()
