# Implementation Plan: Dedicated Income Breakdown Chart

The user wants a new chart specifically for analyzing Income (รายรับ) by category/source. I will add a horizontal bar chart that focuses exclusively on income streams.

## User Review Required

> [!IMPORTANT]
> - **New Chart**: A new section titled **"💰 วิเคราะห์รายรับตามหมวดหมู่"** will be added.
> - **Layout**: This will be a horizontal bar chart similar to the category breakdown, but it will only show income data, making it easier to see where the money is coming from.
> - **Placement**: I will place it immediately after the "Spending Trend" chart and before the "Category Breakdown (Dual)" chart.

## Proposed Changes

### Web (UI)

#### [MODIFY] [ReportsPage.tsx](file:///Users/oatrice/Software-projects/JarWise/Web/src/pages/ReportsPage.tsx)
- Integrate a new `BarChart` section using `data.by_category`.
- Filter or sort the data to show categories with income.
- Apply a consistent Emerald (`#10b981`) color theme for all income-related visuals.

## Verification Plan

### Manual Verification
- Verify the new Income Breakdown chart appears on the Reports page.
- Check that it correctly cycles through 120 months of seeded data (if the "Custom" or "Year" range is selected).
- Ensure the Thai legends and tooltips are correct.
