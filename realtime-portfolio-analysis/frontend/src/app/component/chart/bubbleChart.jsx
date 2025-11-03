"use client";
import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
//import BubbleChartData from "./bubbleChart.json"; // Assuming you have a JSON file with the data
//import BubbleChartStatic from "./bubleChart.json";
import colorPallete from "../../styles/linearColors.json";
import defaultApexOptions from "../../styles/chartTheme";
// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const BubbleChart = ({ chartConfig }) => {
  // Static JSON data for the bubble chart
  //console.log(BubbleChartData,  "BubbleChartData");

  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    if (chartConfig && chartConfig.data) {
      const bubbleChartData = chartConfig.data.bubble_chart;
      const colorsAddedSeries = bubbleChartData.items.map((item) => ({
        ...item,
        color: [colorPallete.bubbleChartColors[item.name]],
      }));
      const series = colorsAddedSeries;

      const options = {
        ...defaultApexOptions,
        chart: {
          ...defaultApexOptions.chart,
          type: "bubble",
        },
        title: {
          text: bubbleChartData.title || "Risk Distribution",
          align: "center",
        },
        xaxis: {
          type: "category",
          //categories: categoryNames,
          title: {
            text: bubbleChartData.x_axis_display_name || "Asset Type",
          },
          labels: {
            rotate: -45,
            rotateAlways: false,
            hideOverlappingLabels: true,
            trim: true,
            //tickAmount: 12,
            //offsetY: 5,
            //maxHeight: 250
          },
        },
        yaxis: {
          title: {
            text: "Investment amount (in USD $)",
          },
          labels: {
            formatter: (val) => `$${val.toLocaleString()}`,
          },
        },
        tooltip: {
          shared: false,
          intersect: true,
          y: {
            formatter: (val) => `$${val.toLocaleString()}`,
            title: {
              formatter: () => "Investment Amount",
            },
          },
          z: {
            formatter: (val) => 'Risk Score - ' + `${val.toLocaleString()}`, // Just the number
          },
        },
        legend: {
          position: "top",
        },
      };
      setChartData({ series, options });
    }
  }, [chartConfig]);

  return (
    <div className="bg-gray-800 shadow-lg px-2 h-full">
      {chartData && chartData.series.length > 0 && (
        <Chart
          options={chartData.options}
          series={chartData.series}
          type="bubble"
          height="95%"
        />
      )}
    </div>
  );
};

export default BubbleChart;
