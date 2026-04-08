# Implementation Plan: Android Reports Styling & Orientation Synchronization

This plan aims to synchronize the visual style of the Android reports dashboard with the Web frontend, specifically focusing on axis colors and chart orientations.

## Goal
1.  **Sync Axis Colors**: Align the X and Y axis label colors with the Web repo (#9ca3af) and set appropriate grid line colors (#374151).
2.  **Chart Orientation**: Determine the best orientation for breakdown charts in Android given the technical constraints of Vico v1.14.0.

## User Review Required

> [!IMPORTANT]
> **Technical Constraint: Horizontal Bars in Vico 1.x**
> Vico version 1.14.0 (the current version used in this project) **does not natively support horizontal bar charts**. This feature was introduced in Vico 2.0.0+.
>
> **Proposed Recommendation:**
> We should **keep the breakdown charts vertical** on Android to avoid unstable hacks or major library upgrades at this stage. However, we will use the exact color scheme from the Web repo (#10b981 for Income, #f43f5e for Expense) to maintain visual harmony.

## Proposed Changes

### [ReportsScreen.kt](file:///Users/oatrice/Software-projects/JarWise/Android/app/src/main/java/com/oatrice/jarwise/ui/reports/ReportsScreen.kt)

#### [MODIFY] [ReportsScreen.kt](file:///Users/oatrice/Software-projects/JarWise/Android/app/src/main/java/com/oatrice/jarwise/ui/reports/ReportsScreen.kt)
- Update `rememberStartAxis` and `rememberBottomAxis` to use custom `axisLabelComponent` with color `#9ca3af`.
- Update `axisLineComponent` and `guidelineComponent` colors to `#374151` (low opacity for guidelines).
- Ensure all charts (Trend, Income, Expense, Comparison) use consistent axis styling.

## Open Questions

> [!QUESTION]
> 1.  Are you okay with keeping the bar charts **vertical** for now due to library constraints, or would you like me to attempt a manual rotation (which might be less stable)?
> 2.  Should I also sync the **Pie Chart** colors with the `PIE_COLORS` array from the Web repo?

## Verification Plan

### Automated Tests
- None (UI styling).

### Manual Verification
- Verify that axis labels are clearly visible but subtle (Gray 400).
- Verify that grid lines are subtle and match the Web dashboard's "dark mode premium" feel.
- Confirm all charts render without compilation errors after these styling changes.
