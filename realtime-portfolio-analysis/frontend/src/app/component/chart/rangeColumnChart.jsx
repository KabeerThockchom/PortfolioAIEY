"use client";
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import defaultApexOptions from "../../styles/chartTheme";
//import WaterfallData from "./waterFall.json";
// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const RangeColumnChart = ({ chartConfig }) => {
  // Static JSON data for the bubble chart

  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    if (chartConfig && chartConfig.data) {
      const waterfallData = chartConfig.data.waterfall_chart;
      const series = [
        {
          data: waterfallData.items.map((item) => {
            return {
              x: item.x,
              y: item.y,
              fillColor:
                item.value_type === "positive"
                  ? "#00a63e"
                  : item.value_type === "negative"
                    ? "#e7000b"
                    : "#155dfc",
            };
          }),
        },
      ];

      const options = {
        ...defaultApexOptions,
        chart: {
          ...defaultApexOptions.chart,
          type: "rangeBar",
        },
        title: {
          text: waterfallData.title, // Add your desired title here
          align: "center",
        },
        xaxis: {
          type: "category", // Use "datetime" if x-axis values are dates
          title: {
            text: waterfallData.x_axis_dislay_name,
          },
          tickAmount: 12,
          
        },
        yaxis: {
          title: {
            text: waterfallData.y_axis_display_name,
          },
          labels: {
            formatter: (value) => {
              const parsedValue = parseFloat(value);
              if (!isNaN(parsedValue)) {
                return `${(parsedValue*100).toFixed(1)}%`;
              }
              // Otherwise, return as is
              return value;
            },
          },
        },
        tooltip: {
          enabled: true,
          custom: function({ series, seriesIndex, dataPointIndex, w }) {
              const data = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
              const category = data.x;
              const low = data.y[0];
              const high = data.y[1];
              const diff = high - low;
              const percent = ((diff) * 100).toFixed(2);

              return `
                <div style="padding: 8px;">
                  <strong>${category} : ${percent}%</strong><br/>
                </div>
              `;
            }
        },
        legend: {
          position: "top",
        },
      };
      setChartData({ series, options });
    }
  }, [chartConfig]);

  return (
    <div className="bg-gray-900 p-4 shadow-lg h-full">
      {chartData && chartData.series.length > 0 && (
        <Chart
          options={chartData.options}
          series={chartData.series}
          type="rangeBar"
          height="100%"
        />
      )}
    </div>
  );
};

export default RangeColumnChart;
