"use client";
import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import defaultApexOptions from "../../styles/chartTheme";
// import BubbleChartData from "./bubbleChart.json";

// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const GaugeChart = ({ chartConfig }) => {
  const [chartData, setChartData] = useState(null);
  useEffect(() => {
    if (chartConfig && chartConfig.items.length > 0) {
      const options = {
        ...defaultApexOptions,
        chart: {
        ...defaultApexOptions.chart,
          type: "radialBar",
          offsetY: -20,
          sparkline: { enabled: true },
        },
        title: {
          text: chartConfig.title || "Portfolio Risk Level",
          align: "center",
        },
        plotOptions: {
          radialBar: {
            startAngle: -90,
            endAngle: 90,
          },
        },
        fill: {
          type: "gradient",
          gradient: {
            shade: "light",
            type: "horizontal",
            shadeIntensity: 0.5,
            gradientToColors: ["#FF0000"], // Red
            inverseColors: false,
            opacityFrom: 1,
            opacityTo: 1,
            stops: [0, 100],
            colorStops: [
              {
                offset: 0,
                color: "#00E396", // Green
                opacity: 1,
              },
              {
                offset: 100,
                color: "#FF0000", // Red
                opacity: 1,
              },
            ],
          },
        },
        labels: [chartConfig.items[0].risk_score],
      };

      const series = [chartConfig.items[0].risk_score * 10]; // Value between 0 and 100
      setChartData({ series, options });
    }
  }, [chartConfig]);

  return (
    <div className="bg-gray-800 px-2 pt-8  shadow-lg h-full">
      {chartData && chartData.series.length > 0 && (
        <Chart
          options={chartData.options}
          series={chartData.series}
          type="radialBar"
          height={250}
        />
      )}
    </div>
  );
};

export default GaugeChart;
