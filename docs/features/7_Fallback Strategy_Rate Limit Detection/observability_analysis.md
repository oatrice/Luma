# LLM Observability Analysis and Routing Recommendation

วันที่วิเคราะห์: 2026-03-19

## วัตถุประสงค์

เอกสารนี้สรุป analysis จากข้อมูลการใช้งาน Luma 24 ชั่วโมง สำหรับ 4 Gemini models เพื่อใช้ตอบ 3 คำถามหลัก:

1. สถานะปัจจุบันของระบบทำอะไรไปแล้วบ้างในเชิง observability และ fallback
2. จากข้อมูล usage ที่มี โมเดลไหนควรเป็น primary และ fallback
3. หากจะพัฒนาไปสู่ automatic model router ควรเก็บ metric อะไร และใช้ logic แบบไหน

## Git History Context

จาก `git log` พบว่ามีงานที่เกี่ยวข้องถูกทำไปแล้วต่อเนื่อง:

| Commit | วันที่ | สิ่งที่ทำไปแล้ว |
|---|---|---|
| `e96e527` | 2026-03-16 | เพิ่ม AI usage logging และ `scripts/ai_usage_report.py` |
| `12a2773` | 2026-03-18 | เพิ่ม `luma_version` ลงใน usage log |
| `fc93f31` | 2026-03-18 | เพิ่มตัวดู usage log ใน action menu |
| `ed42657` | 2026-03-19 | เพิ่ม `error_classifier`, retry logic, per-model timeout และ log `error_type` |
| `c6b26c2` | 2026-03-19 | implement smart fallback ใน core |
| `0fbf52f` | 2026-03-19 | เพิ่ม implementation plan สำหรับ smart fallback และ rate limit detection |

ไฟล์ที่เกี่ยวข้องใน codebase ปัจจุบัน:

- `luma_core/usage_tracker.py`
- `luma_core/llm.py`
- `luma_core/error_classifier.py`
- `scripts/ai_usage_report.py`
- `docs/llm_fallback_chain.md`

สรุปคือ Luma มีพื้นฐาน observability และ fallback แล้ว แต่ยังเป็นระดับ rule-based มากกว่า score-based routing

## Input Data

ข้อมูลดิบที่ใช้วิเคราะห์:

| Model | N | Min(s) | Max(s) | Avg(s) | Errors |
|---|---:|---:|---:|---:|---:|
| gemini-3-flash-preview | 11 | 31.2 | 488.1 | 126.3 | 2 |
| gemini-2.5-flash | 4 | 10.3 | 38.2 | 22.3 | 0 |
| gemini-2.5-pro | 2 | 25.9 | 50.4 | 38.2 | 1 |
| gemini-3-pro-preview | 1 | 451.6 | 451.6 | 451.6 | 2 |

Error detail:

- 2 timeouts `> 5 min`
- 3 output truncations

## Data Quality Caveat

ข้อมูลชุดนี้ยังมี inconsistency ที่ควร note ไว้:

- ตารางรวม `N = 18` แต่คำอธิบายบอกว่ามี `20 API calls`
- `Errors` รวมได้ `5` แต่ไม่ได้บอกชัดว่า count ต่อ `attempt`, ต่อ `request`, หรือเป็น event ซ้อน
- `gemini-3-pro-preview` มี `N = 1` แต่ `Errors = 2` จึงตีความได้ว่าอย่างน้อยมีหลาย attempt ภายใน 1 logical request

ผลคือ analysis นี้เหมาะสำหรับใช้เป็น directional recommendation ไม่ใช่ final production benchmark

## 1. Statistical Deep Dive

### ทำไม Min/Max/Avg ไม่พอ

สำหรับ workload LLM ค่า latency มัก skewed และมี tail หนัก จึงไม่ควรใช้ average เป็นตัวแทน "ประสบการณ์จริง" เพียงตัวเดียว

metric ที่ควรเก็บเพิ่ม:

| Metric | ประโยชน์ |
|---|---|
| `p50` | latency ปกติของระบบ |
| `p90`, `p95`, `p99` | tail latency และ worst-case UX |
| `MAD` หรือ `IQR` | วัด dispersion แบบ robust กว่า variance |
| `success rate` | ผ่านหรือไม่ผ่านในภาพรวม |
| `good response rate` | สำเร็จและไม่ truncate และไม่เกิน SLA |
| `timeout rate` | วัด hard failure |
| `truncation rate` | วัด output completeness |
| `tail ratio = p95 / p50` | วัดความไม่นิ่งของ model |

### Outlier Analysis

#### `gemini-3-flash-preview`

คำนวณจากข้อมูลที่มี:

- `max / min = 488.1 / 31.2 = 15.64x`
- ถ้าตัด outlier `488.1s` ออก average จะลดจาก `126.3s` เหลือประมาณ `90.1s`
- แปลว่าแค่ 1 call ดันค่าเฉลี่ยขึ้นประมาณ `36.2s`

ข้อสรุป:

- latency distribution มี heavy tail ชัดเจน
- แม้ตัด outlier แล้ว model นี้ก็ยังช้ากว่า `gemini-2.5-flash` มาก
- สำหรับ synchronous automation ถือว่าเสี่ยง เพราะ user-facing SLA พังได้จาก call ส่วนน้อยแต่กระทบหนัก

#### `gemini-3-pro-preview`

ข้อสังเกต:

- มีเพียง 1 sample ที่ `451.6s`
- มี error เพิ่มอีก 2 กรณี
- practical behavior ใกล้เคียง "usable only for async/batch"

ข้อสรุป:

- ในมุม ops นี่ไม่ใช่แค่ latency สูง แต่เป็น reliability risk ด้วย
- ยังไม่ควรอยู่บน critical path ของ workflow หลัก

### Recommended "True Performance" View

สำหรับ Luma ควรวัด "true performance" ด้วยชุด metric นี้:

1. `p50 latency`
2. `p95 latency`
3. `good response rate`
4. `timeout rate`
5. `truncation rate`

ถ้าต้องมีเลขเดียวเพื่อใช้ route:

```text
effective_latency = p50 + 0.5 * (p95 - p50)
```

หรือถ้าข้อมูลยังน้อย:

```text
effective_latency = p50 + 2 * MAD
```

## 2. Reliability Analysis for Small N

เมื่อ `N` เล็ก ไม่ควรใช้ raw success rate ตรง ๆ เพราะ noise สูงมาก ควรใช้ smoothing หรือ lower-bound estimate

แนวทางที่เหมาะ:

- `Wilson lower bound` สำหรับ success probability แบบ conservative
- `Beta-Binomial smoothing` สำหรับ success, truncation, timeout
- confidence weighting ตามจำนวน sample เพื่อไม่ให้ model ที่มี `N=1` ได้อันดับสูงเกินจริง

### Suggested Reliability Score

นิยาม `good`:

- request สำเร็จ
- ไม่ timeout
- ไม่ truncation
- latency ไม่เกิน SLA ของ lane นั้น

สูตรแนะนำ:

```python
import math

def wilson_lb(successes, attempts, z=1.28):
    if attempts == 0:
        return 0.0
    p = successes / attempts
    denom = 1 + z * z / attempts
    centre = p + z * z / (2 * attempts)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * attempts)) / attempts)
    return max(0.0, (centre - margin) / denom)


def reliability_score(attempts, good, truncations, effective_latency_s, sla_s=60):
    success_lb = wilson_lb(good, attempts)
    trunc_rate = (truncations + 1) / (attempts + 2)
    latency_score = math.exp(-effective_latency_s / sla_s)
    confidence = 1 - math.exp(-attempts / 10)
    prior = 0.60

    raw = (
        0.55 * success_lb +
        0.25 * latency_score +
        0.20 * (1 - trunc_rate)
    )
    return 100 * (confidence * raw + (1 - confidence) * prior)
```

เหตุผลของสูตรนี้:

- `success_lb` ลงโทษ model ที่ sample ยังน้อย
- `latency_score` ลงโทษ model tail หนัก
- `trunc_rate` จับ quality failure ที่ไม่ใช่ hard error
- `confidence` shrink score เข้าหา prior เมื่อ data ยังน้อย

### Heuristic Interpretation

สำหรับข้อมูลชุดนี้:

| Model | Reliability เชิง heuristic |
|---|---|
| `gemini-2.5-flash` | ดีสุดในชุดข้อมูลปัจจุบัน |
| `gemini-2.5-pro` | น่าจะใช้เป็น fallback สำหรับงานยาก แต่ sample ยังน้อย |
| `gemini-3-flash-preview` | เร็วไม่จริงในเชิง tail และมี stability risk |
| `gemini-3-pro-preview` | ไม่ควรใช้เป็น sync fallback ในตอนนี้ |

## 3. Fallback Chain Design

### Recommendation

สำหรับ production path ของ Luma:

| Role | Model | เหตุผล |
|---|---|---|
| Primary | `gemini-2.5-flash` | เร็วสุดในข้อมูลจริงและ error = 0 |
| Secondary fallback | `gemini-2.5-pro` | ใช้เมื่อ task ยาก, output ยาว, หรือ flash fail |
| Canary only | `gemini-3-flash-preview` | ใช้เก็บ telemetry ไม่ควรเป็น default |
| Async/experimental only | `gemini-3-pro-preview` | ช้าและ unstable เกินไปสำหรับ synchronous path |

### Cost-Effective Architecture

แยก routing เป็น 3 lanes:

| Lane | Trigger | Model Order |
|---|---|---|
| Interactive | งานปกติ, user-facing, ต้องเร็ว | `2.5-flash -> 2.5-pro` |
| Heavy reasoning | prompt ใหญ่, multi-file, expected output ยาว | `2.5-flash -> 2.5-pro` โดย allow early escalation |
| Canary / async batch | เก็บข้อมูลหรือ benchmark | `3-flash-preview` หรือ `3-pro-preview` แบบ opt-in |

ไม่แนะนำ chain แบบนี้สำหรับ sync path:

```text
3-flash-preview -> 2.5-flash -> 2.5-pro -> 3-pro-preview
```

เพราะ preview model ตัวแรกจะกินเวลา tail มากเกินไปก่อนถึง stable model

### Implication for Luma

`docs/llm_fallback_chain.md` และ feature #7 plan เดิมวาง `gemini-3-flash-preview` ไว้ต้น chain เพื่อทดลองใช้งาน แต่จากข้อมูล usage จริง ควรพิจารณาแยก "preview experiment chain" ออกจาก "production chain"

## 4. Error Handling Strategy

### Decision Matrix

| Error Type | Recommended Action |
|---|---|
| `RATE_LIMIT` | switch model ทันที |
| `QUOTA_EXCEEDED` | switch model ทันที |
| `TIMEOUT` บน stable model ครั้งแรก | backoff + retry 1 ครั้ง |
| `TIMEOUT` บน preview model | switch model ทันที |
| `OUTPUT_TRUNCATED` จาก `max_tokens` | retry model เดิมด้วย token limit สูงขึ้น |
| `OUTPUT_TRUNCATED` ซ้ำ | switch ไป model ที่ context/output handling ดีกว่า หรือ split task |
| `UNKNOWN` transient | backoff 1 ครั้งแล้วค่อย switch |

### Exponential Backoff vs Immediate Switching

ใช้ immediate switching เมื่อ:

- เป็น `RATE_LIMIT`
- เป็น `QUOTA_EXCEEDED`
- เป็น timeout บน preview model
- elapsed time เกิน hard SLA ของ lane นั้นแล้ว

ใช้ exponential backoff เมื่อ:

- เป็น timeout รอบแรกบน stable model
- เป็น transport error หรือ unknown transient

ตัวอย่าง:

```python
def next_action(error_type, model, elapsed_s, retry_count, finish_reason=None):
    if error_type in {"RATE_LIMIT", "QUOTA_EXCEEDED"}:
        return "switch_model"

    if error_type == "TIMEOUT":
        if "preview" in model or elapsed_s > 120:
            return "switch_model"
        return "backoff_retry" if retry_count == 0 else "switch_model"

    if error_type == "OUTPUT_TRUNCATED":
        if retry_count == 0 and finish_reason == "max_tokens":
            return "retry_same_with_more_tokens"
        return "switch_or_chunk"

    return "backoff_retry" if retry_count == 0 else "switch_model"
```

### Handling Output Truncation

กฎที่ควรใช้:

1. ถ้า finish reason ชี้ว่า `max_tokens` ชนเพดาน ให้ retry model เดิมก่อน
2. ถ้า prompt/context ใหญ่มากอยู่แล้ว ให้ switch ไป model ที่รองรับงานยาวกว่า
3. ถ้า truncation เกิดซ้ำ 2 ครั้ง ให้ chunk task หรือใช้ continuation prompt

continuation prompt example:

```text
Continue from the last complete section only.
Do not repeat previous content.
Return the remaining output in the same format.
```

## 5. Automated Optimization Roadmap

### Metrics ที่ควร log เพิ่มทันที

`record_llm_event()` ปัจจุบัน log พื้นฐานได้ดี แต่ยังไม่พอสำหรับ router ในอนาคต ควรเพิ่ม field ต่อไปนี้:

| Group | Fields |
|---|---|
| Identity | `request_id`, `attempt_id`, `chain_id`, `router_version`, `route_rank` |
| Prompt shape | `prompt_tokens`, `output_tokens`, `max_tokens`, `input_chars`, `context_window_used_pct` |
| Timing | `queue_ms`, `ttft_ms`, `duration_ms`, `stream_ms` |
| Outcome | `finish_reason`, `is_timeout`, `is_truncated`, `was_fallback`, `sla_breached` |
| Task context | `task_type`, `action`, `sub_action`, `project_key`, `issue_numbers` |
| Quality proxy | `rerun_within_10m`, `accepted_without_retry`, `downstream_tests_passed` |
| Cost | `cost_usd_estimate` |

### Why These Metrics Matter

- percentile latency ต้องใช้ raw event ต่อ attempt
- truncation ต้องแยกจาก generic error
- router ต้องรู้ task type เพราะ model ที่เหมาะกับ `planning` อาจไม่เหมาะกับ `code generation`
- cost-aware routing ต้องมี token/cost estimate

### Suggested Router Structure

```python
from dataclasses import dataclass


@dataclass
class ModelStats:
    success_lb: float
    completeness_rate: float
    speed_score: float
    cost_score: float
    sample_size: int


def rank_models(task, stats):
    candidates = ["gemini-2.5-flash", "gemini-2.5-pro"]

    if task.canary:
        candidates.append("gemini-3-flash-preview")

    def score(model):
        s = stats[model]
        return (
            0.50 * s.success_lb +
            0.20 * s.completeness_rate +
            0.20 * s.speed_score +
            0.10 * s.cost_score
        )

    return sorted(candidates, key=score, reverse=True)


def route_request(task, prompt, stats):
    for model in rank_models(task, stats):
        response = call_model(model, prompt, max_tokens=task.max_tokens)
        log_attempt(task, model, response)

        if response.ok and not response.truncated and response.duration_s <= task.sla_s:
            return response

        action = next_action(
            response.error_type,
            model,
            response.duration_s,
            response.retry_count,
            response.finish_reason,
        )

        if action == "retry_same_with_more_tokens":
            response = call_model(
                model,
                prompt,
                max_tokens=min(task.max_tokens * 2, task.max_cap),
            )
            log_attempt(task, model, response)
            if response.ok and not response.truncated:
                return response

    raise RuntimeError("all candidate models failed")
```

## Recommended Next Steps

ลำดับการทำงานที่ควรทำต่อ:

1. เพิ่ม raw fields ใน `usage_tracker` ให้ครบสำหรับ percentile, truncation, และ routing
2. ขยาย `scripts/ai_usage_report.py` ให้รายงาน `p50`, `p95`, timeout rate, truncation rate
3. แยก chain เป็น `production chain` กับ `preview canary chain`
4. เพิ่ม circuit breaker ต่อ model แทนการจำแค่ fallback index ล่าสุด
5. หลังมี sample มากขึ้นค่อยเปิด score-based automatic routing

## Final Recommendation

จากข้อมูลชุดนี้:

- `gemini-2.5-flash` ควรเป็น primary model สำหรับ Luma production path
- `gemini-2.5-pro` ควรเป็น selective fallback สำหรับงานที่ยากหรือ output ยาว
- `gemini-3-flash-preview` ควรย้ายไป canary หรือ experiment lane
- `gemini-3-pro-preview` ควรจำกัดให้ใช้กับ async batch หรือ manual opt-in

ถ้าต้องมี principle เดียวสำหรับ iteration ถัดไป:

```text
route by observed reliability first, then latency, then cost
```

ไม่ควร route โดยอาศัยชื่อรุ่นหรือ "preview/newer sounds better" เพียงอย่างเดียว
