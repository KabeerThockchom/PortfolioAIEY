'use client';
import React, {useState} from "react";
import dynamic from "next/dynamic";

// Dynamically import the Chart component
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const Graph = () => {
  const [series] = useState([
    {
      name: 'AAPL',
      data: [250, 245, 240, 220, 215, 200, 210, 205, 208],
    },
  ]);

  const [options] = useState({
    chart: {
      type: 'area',
      toolbar: {
        show: true,
      },
      zoom: {
        enabled: false,
      },
    },
    dataLabels: {
      enabled: false,
    },
    stroke: {
      curve: 'smooth',
      width: 2,
      colors: ['#facc15'],
    },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.3,
        opacityTo: 0.1,
        stops: [0, 90, 100],
        colorStops: [
          {
            offset: 0,
            color: '#facc15',
            opacity: 0.5,
          },
        ],
      },
    },
     xaxis: {
      categories: ['Mar `25', '15 Mar', 'Apr `25', '15 Apr', 'May `25', '15 May'],
      labels: {
        style: {
          colors: '#e5e7eb',
        },
      },
    },
    yaxis: {
      labels: {
        style: {
          colors: '#e5e7eb',
        },
      },
    },
    tooltip: {
      theme: 'dark',
    },
    annotations: {
      xaxis: [
        {
          x: '15 May',
          borderColor: '#facc15',
          label: {
            style: {
              color: '#1A1A24',
              background: '#facc15',
            },
            text: 'Dividend: $5.20',
          },
        },
      ],
    },
  });
        return (
        <div className="bg-gray-800 p-4 rounded-xl shadow-lg">
            <div>
          <Chart options={options} series={series} type="area" height={320} />
        </div>

        <div className="text-center">
          <h3 className="text-lg font-bold">AAPL Stock Price</h3>
          <p className="text-[#FFE600] font-semibold">
            Current: $208.78 | $-36.09 (-14.74%)
          </p>
        </div>
        </div>
    )
}
export default Graph;