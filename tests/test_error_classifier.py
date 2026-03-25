
from luma_core.error_classifier import ErrorType, classify_error, is_retryable

def test_classify_rate_limit_429():
    assert classify_error("HTTP Error 429: Too Many Requests") == ErrorType.RATE_LIMIT

def test_classify_resource_exhausted():
    assert classify_error("Error: RESOURCE_EXHAUSTED - quota exceeded") == ErrorType.RATE_LIMIT

def test_classify_quota_exceeded():
    assert classify_error("Gemini API Error: quota exceeded for model") == ErrorType.QUOTA_EXCEEDED

def test_classify_timeout():
    assert classify_error("Gemini CLI timed out after 5 minutes.") == ErrorType.TIMEOUT
    assert classify_error("Read timeout errors") == ErrorType.TIMEOUT

def test_classify_unknown():
    assert classify_error("Some random network exception") == ErrorType.UNKNOWN

def test_is_retryable_timeout():
    assert is_retryable(ErrorType.TIMEOUT) is True

def test_is_retryable_rate_limit():
    assert is_retryable(ErrorType.RATE_LIMIT) is False

def test_is_retryable_quota_exceeded():
    assert is_retryable(ErrorType.QUOTA_EXCEEDED) is False

def test_is_retryable_unknown():
    assert is_retryable(ErrorType.UNKNOWN) is True  # Unknown errors are generally retryable up to max retries
