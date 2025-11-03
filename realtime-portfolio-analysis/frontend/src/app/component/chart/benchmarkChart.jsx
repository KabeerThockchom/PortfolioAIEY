"use client";
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import colorPallete from "../../styles/linearColors.json";
// import serverData from "./server.json";
import defaultApexOptions from "../../styles/chartTheme";

// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const BenchmarkChart = ({ chartConfig }) => {
  const {
    bar_chart_data,
    line_chart_data,
    x_axis_display_name,
    y_axis_bar_display_name,
    y_axis_line_display_name,
    title,
  } = chartConfig.data;

  // State to hold bar and line series
  const [barSeries, setBarSeries] = useState([]);
  const [lineSeries, setLineSeries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [yBarSeries, setYBarSeries] = useState([]);
  const [yLineSeries, setYLineSeries] = useState([]);
  const [palleteColors, setPaletteColors] = useState({});
  const [strokeWidth, setStrokeWidth] = useState([]);

  // Prepare data for the X-axis and bar chart
  useEffect(() => {
    // Collect all unique dates from both bar_chart_data and line_chart_data
    const allDates = new Set([
      ...bar_chart_data.map((item) => item.date),
      ...line_chart_data.flatMap((line) => line.rows.map((row) => row.date)),
    ]);

    // Sort dates for the X-axis
    const sortedDates = Array.from(allDates).sort();

    // Create bar series for each dimension
    const dimensions = Array.from(
      new Set(bar_chart_data.map((item) => item.dimension))
    );

    const paletteMap = dimensions.reduce((acc, dimension, index) => {
      acc[dimension] = colorPallete.chartThemeColors[index];
      return acc;
    }, {});
    setPaletteColors(paletteMap);
    const strokeWidthArr = Array(dimensions.length)
      .fill(1)
      .concat(Array(dimensions.length).fill(3));
    setStrokeWidth(strokeWidthArr);

    const barSeriesData = dimensions.map((dimension, index) => ({
      name: dimension + ":",
      type: "bar",
      data: sortedDates.map((date) => {
        const barData = bar_chart_data.find(
          (item) => item.date === date && item.dimension === dimension
        );
        return barData ? barData.return : null; // Return null if no data
      }),
      color: paletteMap[`${dimension}`],
      showInLegend: false,
    }));
    setYBarSeries([...barSeriesData.map((series) => series.name)]);
    setBarSeries(barSeriesData);
    setCategories(sortedDates);
  }, [bar_chart_data, line_chart_data]);

  // Prepare data for the line chart
  useEffect(() => {
    // Create line series for each display name

    const lineSeriesData = line_chart_data.map((line, index) => ({
      name: line.display_name,
      type: "line",
      data: categories.map(
        (date) => line.rows.find((row) => row.date === date)?.value || 0
      ),
      color: palleteColors[`${line.display_name}`],
      showInLegend: false,
      stroke: { width: 2 },
    }));
    setYLineSeries([...lineSeriesData.map((series) => series.name)]);
    setLineSeries(lineSeriesData);
  }, [line_chart_data, categories]);

  const lineLegendItems = lineSeries.map((s) => s.name);
  const lineLegendColors = lineSeries.map((s) => s.color);
  // Chart options
  const options = {
    ...defaultApexOptions,
    chart: {
   ...defaultApexOptions.chart,
      type: "line",
      stacked: false,
    },
    tooltip: {
      enabled: true,
      custom: function ({ series, seriesIndex, dataPointIndex, w }) {
        // Only show tooltip for line series (not bar series)
        if (seriesIndex >= barSeries.length) {
          return ""; // Hide tooltip for bar series
        }
        const value = series[seriesIndex][dataPointIndex];
        // Do not show tooltip if value is null or undefined
        if (value === null || value === undefined) {
          return "";
        }

        const barSeriesTooltipString = barSeries.map((s, index) => {
          return `<div style="color:${s.color};">${s.name}</div><div style="color:${s.color};">Percentage: ${series[index][dataPointIndex]}%</div>`;
        });
        return `<div style="padding:8px;">
      ${barSeriesTooltipString}
      </div>`;
      },
    },
    plotOptions: {
      bar: {
        columnWidth: "15px",
      },
    },
    fill: {
      opacity: 0.5, // Set bar opacity to 50%
    },
    stroke: {
      width: strokeWidth, // Set bar width to 0 and line width to 2
    },
    title: {
      text: title || "Portfolio Benchmark",
      align: "center",
      ...defaultApexOptions.title.style,
    },
    xaxis: {
      categories: categories,
      axisTicks: {
        show: false, // Remove ticks from x-axis
      },
      title: {
        text: x_axis_display_name || "Date",
      },
      labels: {
        formatter: (value) => {
          const isQuarterPresent = bar_chart_data.find(
            (item) => item.date === value
          );
          return isQuarterPresent ? isQuarterPresent.quarter : "";
        },
      },
    },
    yaxis: [
      {
        seriesName: yLineSeries, // Use the names of the bar series for the Y-axis

        title: {
          text: y_axis_line_display_name || "Index Value",
        },
        labels: {
          formatter: (value) => `$${Math.round(value)}`, // Remove decimal points & add $$ symbol
        },
      },
      {
        opposite: true,
        seriesName: yBarSeries,

        title: {
          text: y_axis_bar_display_name || "Returns (%)",
        },
        labels: {
          formatter: (value) => `${Math.round(value)}%`, // Remove decimal points & add percentage sign
        },
      },
    ],

    legend: {
      show: true,
      position: "top",
      horizontalAlign: "center",
      width: "100%",
      clusterGroupedSeriesOrientation: "horizontal",
      customLegendItems: lineLegendItems, // Only line series names
      markers: {
        fillColors: lineLegendColors, // Only line series colors
      },
    },
  };

  // Combine bar and line series
  const series = [...barSeries, ...lineSeries];
  return (
    <div className="bg-gray-800 p-4 rounded-xl shadow-lg h-full">
      <Chart options={options} series={series} type="line" height="100%" />
    </div>
  );
};

export default BenchmarkChart;
