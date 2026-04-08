# Walkthrough: Custom Date Range Reports

I have successfully implemented the "Custom Date Range" and "All Time" reporting features across both the Web and Android platforms. This allows you to analyze your financial data over any period, including multiple years.

## Changes Made

### 📱 Android (Compose)
- **New Filter Chips**: Added "All" (All-time) and "Custom" to the report range selector.
- **Material3 DateRangePicker**: Integrated a standard Android date range picker when "Custom" is selected.
- **ViewModel Updates**: `ReportsViewModel` now handles arbitrary start and end dates for both fetching reports and exporting CSVs.

### 🌐 Web (React)
- **Enhanced Range Toggle**: Added "ทั้งหมด" (All) and "กำหนดเอง" (Custom) options.
- **Dynamic UI**: Selecting "กำหนดเอง" expands a section with Start and End date inputs.
- **Robust API Calls**: Updated `fetchReport` and `handleExport` logic to prioritize custom dates when provided.

## How to use

### On Android
1. Open the **Reports** screen.
2. Tap on the **Custom** chip.
3. Select your desired start and end dates in the calendar picker and tap **Confirm**.
4. To view everything, simply tap the **All** chip.

### On Web
1. Navigate to the **Reports** page.
2. Click the **กำหนดเอง (Custom)** button.
3. Choose your Start and End dates in the inputs that appear.
4. Click the **📈 (Analyze)** button to load the data.

## Verification
- [x] Verified that selecting "All" fetches data from the year 2000 to today.
- [x] Verified that picking a 2-year custom range correctly updates the Income/Expense summary and charts.
- [x] Verified that CSV Export correctly respects the custom date range.

> [!TIP]
> Use the **All** option for a quick overview of your lifetime financial progress in JarWise!
