from luma_core.actions import _build_code_review_followup_prompt


def test_build_code_review_followup_prompt_single_repo():
    prompt = _build_code_review_followup_prompt()

    assert (
        prompt
        == "นำ code review จาก code_review.md "
        "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) มาอธิบาย "
        "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
        "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
    )
    assert "terminal" not in prompt


def test_build_code_review_followup_prompt_multi_repo():
    prompt = _build_code_review_followup_prompt(multi_repo=True)

    assert (
        prompt
        == "นำ code review จาก code_review.md "
        "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) ในทุก repo มาอธิบาย "
        "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
        "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
    )
    assert "terminal" not in prompt
