from backend.services.reflection_service import requires_buffered_validation


def test_normal_high_confidence_question_can_stream():
    assert not requires_buffered_validation("报销流程是什么", [{"score": 0.82, "visibility": "internal"}], has_images=False)


def test_sensitive_low_confidence_or_image_requests_are_buffered():
    assert requires_buffered_validation("管理员密码重置流程", [{"score": 0.9}], has_images=False)
    assert requires_buffered_validation("介绍制度", [{"score": 0.2}], has_images=False)
    assert requires_buffered_validation("分析图片", [{"score": 0.9}], has_images=True)
