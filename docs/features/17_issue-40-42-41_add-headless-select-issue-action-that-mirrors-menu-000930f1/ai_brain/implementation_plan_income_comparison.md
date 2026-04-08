# Implementation Plan: Enriching Income Analysis & Data

The goal is to provide a more detailed income breakdown by category, comparing the current period with the previous one, and enriching the 10-year historical dataset with more varied income sources.

## User Review Required

> [!IMPORTANT]
> - **Income Comparison**: The "💰 วิเคราะห์รายรับตามหมวดหมู่ (Income Breakdown)" chart will now show two bars: **รายรับปัจจุบัน** (Current Income) and **รายรับช่วงก่อนหน้า** (Previous Income).
> - **Income Distribution**: Adding a new section **"💰 สัดส่วนรายรับตามหมวดหมู่ (Distribution)"** featuring a Pie Chart to mirror the Expense Distribution chart.
> - **Data Diversity**: I will enrich the 10-year dataset with multiple income sources per month distributed across various jars for realistic visualization.

## Proposed Changes

### Backend (Service)

#### [MODIFY] [report_service.go](file:///Users/oatrice/Software-projects/JarWise/Backend/internal/service/report_service.go)
- Update the merge logic in `GenerateReport` to populate `PrevIncome` for both `ByCategory` and `ByJar` lists.

### Backend (Seeding)

#### [MODIFY] [seed-10-years/main.go](file:///Users/oatrice/Software-projects/JarWise/Backend/cmd/seed-10-years/main.go)
- Add more income sources to the monthly generation loop.
- Randomize descriptions and target jars for these new income transactions.

### Web (UI)

#### [MODIFY] [ReportsPage.tsx](file:///Users/oatrice/Software-projects/JarWise/Web/src/pages/ReportsPage.tsx)
- Add a second `<Bar>` to the Income Breakdown `BarChart` for `prev_income`.
- Implement the new **"💰 สัดส่วนรายรับตามหมวดหมู่ (Distribution)"** Pie Chart section.
- Sync colors and terminology across all charts.

## Verification Plan

### Automated Tests
- Run `go run cmd/seed-10-years/main.go` to ensure the dataset is successfully generated.
- Verify the backend response manually via `curl` or by checking the network tab in the browser.

### Manual Verification
- View the "Income Breakdown" chart in the web app.
- Confirm that two bars appear for categories with historical income.
- Verify that Thai labels and tooltips correctly identify "รายรับช่วงก่อนหน้า".
