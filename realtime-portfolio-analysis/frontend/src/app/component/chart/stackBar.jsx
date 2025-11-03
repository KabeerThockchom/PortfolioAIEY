"use client";
import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
//import columnChartData from "./columnChart.json";
import defaultApexOptions from "../../styles/chartTheme";

// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const StackBar = ({ chartConfig }) => {
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    // Update chart data when chartConfig changes
    if (chartConfig && chartConfig.data) {
      const stackBarData = chartConfig.data;
      const stackBarChart = {
        series: stackBarData.stack_bar_data.map((item) => {
          return {
            name: item.name,
            data: item.data,
          };
        }),
        options: {
          ...defaultApexOptions,
          chart: {
            ...defaultApexOptions.chart,
            type: "bar",
            stacked: false,
          },
          title: {
            text: stackBarData.title,
            align: "center",
          },
          stroke: {
            width: 1,
          },
          dataLabels: {
            enabled: true,
            formatter: (_, opts) => {
              const dataName =
                stackBarData.stack_bar_data[opts.seriesIndex].data_name[
                  opts.dataPointIndex
                ];
              return dataName;
            },
          },
          plotOptions: {
            bar: {
              horizontal: false,
            },
          },
          xaxis: {
            categories: stackBarData.x_axis_data,
          },
          yaxis: {
            title: {
              text: stackBarData.y_axis_display_name,
            },
          },
          fill: {
            opacity: 1,
          },
          legend: {
            show: false,
          },
          tooltip: {
            enabled: true,
            custom: function ({ series, seriesIndex, dataPointIndex }) {
              const dataName =
                stackBarData.stack_bar_data[seriesIndex].data_name[
                  dataPointIndex
                ];
              return `<div style="padding:8px;">
                <strong>${dataName}</strong>: ${series[seriesIndex][dataPointIndex]}
              </div>`;
            },
          },
        },
      };
      setChartData(stackBarChart);
    }
  }, [chartConfig]);

  return (
    <div className="p-4 rounded-xl shadow-lg h-full">
      {chartData && chartData.series.length > 0 && (
        <Chart
          options={chartData.options}
          series={chartData.series}
          type="bar"
          height="100%"
        />
      )}
    </div>
  );
};

export default StackBar;
