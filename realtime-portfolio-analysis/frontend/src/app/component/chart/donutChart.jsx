"use client";
import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import defaultApexOptions from "../../styles/chartTheme";
import colorPallete from "../../styles/linearColors.json";

// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const getSubsetKeys = (data) =>
  data?.subsets ? Object.keys(data.subsets) : [];

const getIsMultiLevel = (data) =>
  !!(data && data.subsets && Object.keys(data.subsets).length > 0);

const generateColorShades = (hex, count = 3) => {
  const opacities = ["80", "60", "40"]; // 50%, 38%, 25%
  return opacities.slice(0, count).map(op => hex + op);
};

const DynamicChart = ({ chartConfig }) => {
  const [isSubsetView, setIsSubsetView] = useState(false);
  const [chartKey, setChartKey] = useState(0);
  const [series, setSeries] = useState([]);
  const [labels, setLabels] = useState([]);
  const [colors, setColors] = useState([]);
  const [subsetLabel, setSubsetLabel] = useState(null);


  const firstLevelColors = colorPallete.chartThemeColors;

  const prepareChartData = (data, chartType, subsetKey = null) => {
    // --- BAR ---
    if (chartType === "bar") {
      if (getIsMultiLevel(data)) {
        const subsetKeys = getSubsetKeys(data);
        //const allLabels = data.subsets[subsetKeys[0]].labels; 
        const allLabels = Array.from(
          new Set(subsetKeys.flatMap((key) => data.subsets[key].labels))
        );
        const swappedSeries = allLabels.map((label, idx) => ({
          name: label,
          data: subsetKeys.map((key) => {
            const subset = data.subsets[key];
            const i = subset.labels.indexOf(label);
            return i !== -1 ? subset.data[i] : 0;
          }),
        }));
        return {
          series: swappedSeries,
          labels: data.labels,
          colors: colorPallete.chartThemeColors,
          stacked: true,
        };
      }
      return {
        series: [
          {
            name: chartConfig?.title || "Value",
            data: data.datasets.data || [],
          },
        ],
        labels: data.labels || [],
        colors: data.datasets.backgroundColor || colorPallete.chartThemeColors,
        stacked: false,
      };
    }

    // --- DONUT ---
    if (chartType === "donut") {
      if (subsetKey && data?.subsets?.[subsetKey]) {
        const subset = data.subsets[subsetKey];
        const parentIdx = (data.labels_ids || data.labels || []).indexOf(subsetKey);
        let shades = [];
        if (parentIdx !== -1) {
          const baseColor = firstLevelColors[parentIdx % firstLevelColors.length];
          for (let i = 0; i < subset.labels.length; i++) {
            shades.push(generateColorShades(baseColor, 3)[i % 3]);
          }
        } else {
          shades = firstLevelColors.flatMap(c => generateColorShades(c, 1));
        }
        return {
          series: subset.data,
          labels: subset.labels,
          colors: shades,
        };
      }
      return {
        series: data.datasets.data || [],
        labels: data.labels || [],
        colors: firstLevelColors,
      };
    }

    if (chartType === "mixed_chart") {
      if (getIsMultiLevel(data)) {
        const subsetKeys = getSubsetKeys(data);
        const allLabels = Array.from(
          new Set(subsetKeys.flatMap((key) => data.subsets[key].labels))
        );
        const types = ["column", "line", "area"];
        const mixedSeries = subsetKeys.map((key, idx) => ({
          name: data.labels?.[idx] || key,
          type: types[idx % types.length],
          data: allLabels.map((label) => {
            const subset = data.subsets[key];
            const i = subset.labels.indexOf(label);
            return i !== -1 ? subset.data[i] : 0;
          }),
        }));
        return {
          series: mixedSeries,
          labels: allLabels,
          colors: colorPallete.chartThemeColors,
        };
      }
      let datasets = data.datasets;
      if (Array.isArray(datasets)) {
        return {
          series: datasets,
          labels: data.labels || [],
          colors: datasets.map(
            (s, idx) =>
              s.color ||
              colorPallete.chartThemeColors[
                idx % colorPallete.chartThemeColors.length
              ]
          ),
        };
      } else {
        return {
          series: [
            {
              name: chartConfig?.title || "Bar",
              type: "column",
              data: datasets.data || [],
            },
            {
              name: chartConfig?.title || "Line",
              type: "line",
              data: datasets.data || [],
            },
          ],
          labels: data.labels || [],
          colors: datasets.backgroundColor || colorPallete.chartThemeColors,
        };
      }
    }

    return { series: [], labels: [], colors: [] };
  };

  useEffect(() => {
    const { series, labels, colors } = prepareChartData(
      chartConfig.data,
      chartConfig.chartType,
      subsetLabel
    );
    setSeries(series);
    setLabels(labels);
    setColors(colors);
    setChartKey((prevKey) => prevKey + 1);
  }, [chartConfig, isSubsetView, subsetLabel]);

  const handleDataPointSelection = (dataPointIndex) => {
    if (!getIsMultiLevel(chartConfig.data)) return;
    const labelIds = chartConfig.data.labels_ids || [];
    const selectedLabelId = labelIds[dataPointIndex];
    if (selectedLabelId && chartConfig.data.subsets[selectedLabelId]) {
      setSubsetLabel(selectedLabelId);
      setIsSubsetView(true);
    }
  };

  const handleBackButtonClick = () => {
    setSubsetLabel(null);
    setIsSubsetView(false);
  };

  let options = {
    ...defaultApexOptions,
    chart: {
      ...defaultApexOptions.chart,
      type:
        chartConfig.chartType === "mixed_chart"
          ? "line"
          : chartConfig.chartType === "bar" && getIsMultiLevel(chartConfig.data)
          ? "bar"
          : chartConfig.chartType,
      ...(getIsMultiLevel(chartConfig.data) &&
        chartConfig.chartType !== "donut" && {
          stacked: true,
        }),
      events: {},
    },
    ...(chartConfig.chartType === "bar" && {
      yaxis: {
        title: {
          text: "Investment Amount (USD)",
        },
        labels: {
          formatter: (val) => `$${val}`,
        },
      },
    }),
    colors: colors,
    legend: { position: "bottom" },
    title: {
      text: chartConfig?.title || "Chart",
      align: "center",
      style: { color: "#fff", fontSize: "20px" },
    },
    tooltip: {
      y: {
        formatter: (val) => (typeof val === "number" ? `$${val.toFixed(2)}` : val),
      },
    },
    grid: { borderColor: "#444" },
  };

  if (
    getIsMultiLevel(chartConfig.data) &&
    !isSubsetView &&
    (chartConfig.chartType === "donut" ||
      chartConfig.chartType === "bar" ||
      chartConfig.chartType === "mixed_chart")
  ) {
    options.chart.events.dataPointSelection = function (
      event,
      chartContext,
      config
    ) {
      handleDataPointSelection(config.dataPointIndex);
    };
    options.chart.cursor = "pointer";
  }

  if (chartConfig.chartType === "donut") {
    options = {
      ...options,
      labels: labels,
      plotOptions: {
        pie: {
          donut: {
            labels: {
              show: true,
              value: {
                show: true,
                fontSize: "20px",
                fontWeight: 700,
                formatter: function (val) {
                  return `$${parseFloat(val).toFixed(2)}`;
                }
              },
              total: {
                show: true,
                label: subsetLabel || "Total",
                fontSize: "20px",
                fontWeight: 700,
                formatter: function (w) {
                  const total = w.globals.series.reduce((sum, v) => sum + v, 0);
                  return `$${total.toFixed(2)}`;
                }
              }
            }
          }
        }
      }
    };
  }

  if (
    chartConfig.chartType === "bar" ||
    chartConfig.chartType === "mixed_chart"
  ) {
    options = {
      ...options,
      xaxis: {
        categories: labels,
        labels: { style: { colors: "#fff" } },
      },
      dataLabels: { enabled: true, style: { colors: ["#fff"] } },
      ...(getIsMultiLevel(chartConfig.data) && {
        plotOptions: {
          bar: {
            horizontal: false,
            borderRadius: 6,
            columnWidth: "40%",
          },
        },
      }),
      ...(chartConfig.chartType === "mixed_chart" && {
        stroke: { width: [3, 3, 3] },
      }),
    };
  }

  const chartType =
    chartConfig.chartType === "mixed_chart"
      ? "line"
      : chartConfig.chartType === "bar" && getIsMultiLevel(chartConfig.data)
      ? "bar"
      : chartConfig.chartType;

  return (
    <div className="bg-gray-900 p-4 rounded-xl shadow-lg h-full">
      <div className="flex items-center justify-between h-[10%] mb-4">
        {isSubsetView && (
          <button
            onClick={handleBackButtonClick}
            className="bg-blue-500 text-white px-4 py-2 rounded mb-4"
          >
            Back
          </button>
        )}
      </div>
      <Chart
        key={chartKey}
        options={options}
        series={series}
        type={chartType}
        width="100%"
        height="90%"
      />
    </div>
  );
};

export default DynamicChart;
