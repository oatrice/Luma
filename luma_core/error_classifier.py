from enum import Enum
import re

class ErrorType(Enum):
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    OUTPUT_TRUNCATED = "OUTPUT_TRUNCATED"
    UNKNOWN = "UNKNOWN"

def classify_error(error_msg: str) -> ErrorType:
    """Classify an LLM error message into standard ErrorType."""
    if not error_msg:
        return ErrorType.UNKNOWN
        
    error_msg = str(error_msg).lower()
    
    # Rate Limit
    if re.search(r'\b(429|too many requests|resource_exhausted)\b', error_msg):
        return ErrorType.RATE_LIMIT
        
    # Quota Exceeded (Sometimes overlaps with 429 depending on API)
    if 'quota' in error_msg:
        return ErrorType.QUOTA_EXCEEDED
        
    # Timeout
    if 'timeout' in error_msg or 'timed out' in error_msg:
        return ErrorType.TIMEOUT
        
    # Truncated Output (specific to Luma's handling of partial responses)
    if 'truncated' in error_msg or 'incomplete' in error_msg:
        return ErrorType.OUTPUT_TRUNCATED
        
    return ErrorType.UNKNOWN

def is_retryable(error_type: ErrorType) -> bool:
    """Determine if an error type should be retried on the SAME model."""
    # We DO NOT retry rate limits or quotas on the same model - we want to fail fast and fallback
    if error_type in (ErrorType.RATE_LIMIT, ErrorType.QUOTA_EXCEEDED):
        return False
        
    # We DO retry timeouts (could be a temporary network blip) and unknowns
    return True
