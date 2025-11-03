'use client';
import React, {useState, useEffect} from "react";
import dynamic from "next/dynamic";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const LineAreaChart = () => {
   const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/json/lineAreaChart.json");
        if (!response.ok) throw new Error("Failed to fetch data");
        const jsonData = await response.json();
        setChartData(jsonData);
      } catch (err) {
        setError(err.message);
      }
    };
    fetchData();
  }, []);

   const title = chartData?.title;
  const description = chartData?.description;
  const data = chartData?.data;
  const statistics = chartData?.statistics;

  const chartOptions = {
      chart: {
        type: "area",
        toolbar: { show: true },
        zoom: { enabled: false },
        background: "transparent",
      },
      dataLabels: { enabled: false },
      stroke: {
        curve: "smooth",
        width: 2,
        colors: data ? [data.datasets[0].borderColor] : [],
      },
      fill: {
        type: "gradient",
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.3,
          opacityTo: 0.1,
          stops: [0, 90, 100],
        },
      },
      xaxis: {
        categories: data ? data.labels : [],
        labels: {
          style: {
            colors: "#e5e7eb",
            fontSize: "10px",
          },
        },
      },
      yaxis: {
        labels: {
          style: {
            colors: "#e5e7eb",
            fontSize: "10px",
          },
        },
      },
      tooltip: { theme: "dark" },
      annotations: {
        xaxis: [
          {
            x: "May 15",
            borderColor: "#facc15",
            label: {
              style: {
                color: "#1A1A24",
                background: "#facc15",
                fontSize: "10px",
              },
              text: "Dividend: $5.20",
            },
          },
        ],
      },
    };

  const chartSeries = 
      data
        ? data.datasets.map((ds) => ({
            name: ds.label,
            data: ds.data,
          }))
        : []
    
        };

   if (error) return <div className="text-red-500">{error}</div>;
  if (!chartData) return <div>Loading...</div>;

        return (
        <div className="bg-gray-800 p-2 rounded-lg shadow mt-10 mx-2 mb-2 border border-white">
          {/* <GraphData /> */}
           <div className="text-center mt-1">
        <h3 className="text-sm font-bold text-white">
          {title || "Chart Title"}
        </h3>
        <p className="text-[#FFE600] text-xs font-mediun">
          Current: {statistics["Current Price"]} | {statistics["Change"]}
        </p>
      </div>
      <div className="mt-2">
        <Chart
          options={chartOptions}
          series={chartSeries}
          type="area"
          height={150}
        />
      </div>
      {/* <ChartInformation statistics={statistics} exchange={chartData.exchange} /> */}
        </div>
    )
export default LineAreaChart;