# Implementation Plan: Refactoring Financial Visualization & Data Seeding

The goal is to provide a cleaner separation between Income and Expense analysis and enrich the historical dataset with more varied income sources.

## User Review Required

> [!IMPORTANT]
> - **Data Seeding**: I will add **2-3 varied income sources** per month (Side Hustle, Dividend, etc.) distributed across different jars, instead of just a single Salary entry.
> - **UI - Expense Breakdown**: The primary category chart will be renamed to **"📊 วิเคราะห์รายจ่ายตามหมวดหมู่ (Expense Breakdown)"** and will only show expenses (Current vs Previous).
> - **UI - Income Breakdown**: The income chart will be renamed to **"💰 วิเคราะห์รายรับตามหมวดหมู่ (Income Breakdown)"** to be consistent with the expense section.

## Proposed Changes

### Backend (Seeding)

#### [MODIFY] [seed-10-years/main.go](file:///Users/oatrice/Software-projects/JarWise/Backend/cmd/seed-10-years/main.go)
- Add a loop to generate multiple income transactions per month.
- Randomize descriptions and target jars for these income entries.

### Web (UI)

#### [MODIFY] [ReportsPage.tsx](file:///Users/oatrice/Software-projects/JarWise/Web/src/pages/ReportsPage.tsx)
- Rename headers in the TSX layout.
- Remove the `<Bar dataKey="income" ... />` from the "Expense Breakdown" chart.
- Ensure tooltips and legends match the new single-focus charts.

## Verification Plan

### Automated Tests
- Rerun `go run cmd/seed-10-years/main.go` and verify successful execution.

### Manual Verification
- Open the Reports page in the browser.
- Verify the "Expense Breakdown" chart no longer shows green bars.
- Verify the "Income Breakdown" chart now shows multiple categories (Salary, Freelance, etc.).
- Confirm all Thai labels are correctly updated.
