# Walkthrough: New Area Chart & Thai Legends

I have successfully added a new "Volume" chart and localized all chart legends to Thai for a more professional and intuitive reporting experience.

## Changes Made

### 📊 New Area Chart (Volume)
- **Component**: Added a modern **AreaChart** below the standard line chart.
- **Visuals**: Uses **Soft Gradients** (Emerald for Income, Rose for Expense) to provide a "Glow" effect, making the volume of money flow more visually apparent.
- **X-Axis**: Fixed to show time-series data correctly across all ranges (Month, Year, Custom).

### 🏷️ Localized Legends
- **Name Mapping**: Explicitly updated all chart components (`Line` and `Area`) to use **Thai Legends**:
    - **รายรับ** (Income)
    - **รายจ่าย** (Expense)
- **Consistency**: Both the Line Chart and the new Area Chart now share the same clear, localized labeling.

## Verification

### UI Verification
1.  Open the **Reports** page.
2.  Observe the first chart (**📈 แนวโน้มรายรับ-รายจ่าย**) now has Thai legends at the bottom.
3.  Scroll down to see the new **🌊 ปริมาณรวมรายวัน (Volume)** chart with its premium shaded areas.
4.  Verify that hover tooltips correctly identify "รายรับ" and "รายจ่าย" in the legend and data points.

> [!TIP]
> The **Area Chart** is particularly useful for visualizing "Money Flow Volume" when looking at long-term trends (like the 10-year data we seeded earlier).
