# Implementation Plan: Fix Missing Income Breakdown Chart

The Income Breakdown chart is currently hidden because the seeded income data is not associated with any specific jar/category, leading to a zero-sum across all categories. I will update the frontend to include an "Uncategorized" entry for income that doesn't belong to a specific jar.

## User Review Required

> [!IMPORTANT]
> - **Uncategorized Income**: I will calculate the difference between the total income and the sum of categorized income.
> - **Display**: If there is "Uncategorized Income" (like your Salary in the current seed), it will show up as **"อื่นๆ / ยังไม่จัดลำดับ"** (Others / Uncategorized) in the chart.
> - **Visibility**: This will ensure the chart is always visible if there is any income at all.

## Proposed Changes

### Web (UI)

#### [MODIFY] [ReportsPage.tsx](file:///Users/oatrice/Software-projects/JarWise/Web/src/pages/ReportsPage.tsx)
- Calculate `totalCategorizedIncome`.
- If `totalIncome > totalCategorizedIncome`, push an extra object to the data array for the chart.
- Update the chart condition to check for `data.summary.income > 0` instead.

## Verification Plan

### Manual Verification
- Refresh the Reports page and verify that "💰 วิเคราะห์รายรับรายโถ (Income Breakdown)" now appears.
- Ensure the "อื่นๆ / ยังไม่จัดลำดับ" entry correctly reflects the Salary from the seed data.
