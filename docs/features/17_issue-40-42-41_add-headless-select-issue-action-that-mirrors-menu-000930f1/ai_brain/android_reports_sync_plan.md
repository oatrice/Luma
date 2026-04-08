# Implementation Plan: Android Reports Feature Parity

Sync the Android `Reports` dashboard with the Web frontend's enhanced features, including 10-year historical data visualization, income/expense symmetry, and a premium design aesthetic.

## User Review Required
> [!IMPORTANT]
> - The Android app will switch to **Thai localization** for the Reports screen to match the Web version.
> - We will implement **Dual Breakdowns** (Income and Expense) instead of the current combined view.
> - **Area Charts** with gradients will replace the standard line charts.

## Proposed Changes

### [Backend/DTO Layer]
#### [MODIFY] [ReportDto.kt](file:///Users/oatrice/Software-projects/JarWise/Android/app/src/main/java/com/oatrice/jarwise/data/model/ReportDto.kt)
- Add `prev_income` and `prev_expense` fields to `CategoryAmountDto` and `JarAmountDto`.

### [ViewModel Layer]
#### [MODIFY] [ReportsViewModel.kt](file:///Users/oatrice/Software-projects/JarWise/Android/app/src/main/java/com/oatrice/jarwise/ui/reports/ReportsViewModel.kt)
- Refactor `ReportsUiState` to include:
    - `incomeTrendProducer` and `expenseTrendProducer` (or combined for AreaChart).
    - `incomeBreakdownProducer` and `expenseBreakdownProducer`.
    - `jarDistribution` (separate for Income and Expense if needed, though Backend aggregates by `ByJar`). 
    - Note: Web uses `ByJar` for Expense Distribution and `ByCategory` with `income > 0` for Income Distribution. I will follow this pattern.
- Update `updateUiState` logic to populate comparisons for both income and expense breakdowns.

### [UI Layer]
#### [MODIFY] [ReportsScreen.kt](file:///Java/com/oatrice/jarwise/ui/reports/ReportsScreen.kt)
- **Localization**: Change all titles/labels to Thai.
- **Summary Section**: Update `SummaryCard` to use `฿#,###.##` format and add premium gradients.
- **Trend Section**: Convert `Chart` to an `AreaChart` with gradients for both Income and Expense lines.
- **Breakdown Sections**: 
    - Create two distinct sections: **วิเคราะห์รายรับ** (Income Breakdown) and **วิเคราะห์รายจ่าย** (Expense Breakdown).
    - Use horizontal bar charts with historical comparison (Current vs Prev).
- **Distribution Sections**:
    - Implement **สัดส่วนรายรับ** and **สัดส่วนรายจ่าย** using Pie Charts (Custom Canvas implementation).
- **Comparison Section**: Standardize the "⚖️ เปรียบเทียบ" section to match the Web version.
- **Animations**: Add staggered fade-in animations using `AnimatedVisibility` or `Transition`.

## Open Questions
- Should I use a specific Android Charting library for the Pie Chart or implement a custom Canvas one? (I will proceed with a custom Compose Canvas implementation for maximum control and premium feel).

## Verification Plan
### Automated Tests
- N/A for UI sync, but will check build status.

### Manual Verification
- Deploy to Android Emulator/Device and verify:
    - Income distribution is visible.
    - Breakdowns show current vs previous bars.
    - Trend chart uses gradients.
    - Localization is correct.
    - Sequential animations work as expected.
