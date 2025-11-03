'use client';
import React from "react";
import Chart from "react-apexcharts";
// import ChartInformation from "../chartInfo/chartInformation";
// import GraphData from "./graphData";

const StackBarChart = ({ chartConfig }) => {
  // Use chartConfig directly from props
  const chartData = chartConfig;

  if (!chartData || !chartData.bar_chart_data || chartData.bar_chart_data.length === 0) {
    return <div>No chart data available</div>;
  }

  const title = chartData.title || "Chart Title";
  const description = chartData.description || "";
  const statistics = chartData.statistics;
  const exchange = chartData.exchange || "NMS";

  // Handle new bar_chart_data format
  const barChartData = chartData.bar_chart_data || [];

  // x-axis: labels
  const xCategories = barChartData.map(item => item.label);

  // Get all unique bar names (series)
  const allBars = Array.from(new Set(barChartData.flatMap(item => item.bar)));

  // Build series: for each bar, collect returns for each label (x-axis)
  const chartSeries = allBars.map(barName => {
    const data = barChartData.map(item => {
      const idx = item.bar.indexOf(barName);
      return idx !== -1 ? item.return[idx] : 0;
    });
    return { name: barName, data };
  });

  // Assign colors
  const colorMap = {
    VOO: "#1f77b4",
    SPX: "#d62728",
    AGG: "#2ca02c",
    VBF: "#ff7f0e",
    TLT: "#9467bd"
  };

  const chartOptions = ({
    chart: {
      type: "bar",
      background: "transparent",
      toolbar: { show: true },
      zoom: { enabled: false },
      height: '100%',
      width: '100%',
    },
    dataLabels: { enabled: false },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: "55%",
        endingShape: "rounded",
      },
    },
    colors: allBars.map(bar => colorMap[bar] || "#ccc"),
    grid: { borderColor: "#4b5563", strokeDashArray: 4 },
    xaxis: {
      categories: xCategories,
      title: {
        text: chartData?.x_axis_display_name || "Date",
        style: { color: "#e5e7eb", fontSize: "12px" }
      },
      labels: {
        style: { colors: "#e5e7eb", fontSize: "10px" },
      },
      axisBorder: { color: "#6b7280" },
      axisTicks: { color: "#6b7280" },
      type: 'category',
    },
    yaxis: {
      title: {
        text: chartData?.y_axis_display_name || "Return (%)",
        style: { color: "#e5e7eb", fontSize: "12px" }
      },
      labels: {
        formatter: val => `${val.toFixed(1)}%`,
        style: { colors: "#e5e7eb", fontSize: "10px" },
      },
    },
    tooltip: {
      theme: "dark",
      y: { formatter: val => `${val.toFixed(2)}%` },
    },
    legend: {
      labels: { colors: '#fff' },
    },
  });

  return (
    <div className="bg-gray-800 p-2 rounded-lg shadow mt-10 mx-2 mb-2 border border-white h-full flex flex-col">
      {/* <GraphData /> */}
      <div className="text-center mt-1">
        <h3 className="text-sm font-bold text-white">{title}</h3>
        <p className="text-[#FFE600] text-xs font-mediun">{description}</p>
      </div>
      <div className="flex justify-end mb-2">
        {/* <button className="bg-gray-700 text-gray-300 px-3 py-1 rounded text-xs">
          Range: 3mo
        </button> */}
      </div>
      <div className="flex-1 flex items-center justify-center mt-2 w-full h-full">
        <Chart
          options={chartOptions}
          series={chartSeries}
          type="bar"
          height="100%"
          width="100%"
          style={{ width: '100%', height: '100%' }}
        />
      </div>
      {/* <ChartInformation statistics={statistics} exchange={exchange} /> */}
    </div>
  );
};

export default StackBarChart;
