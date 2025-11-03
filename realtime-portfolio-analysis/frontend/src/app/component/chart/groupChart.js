'use client';
import React from "react";
import dynamic from "next/dynamic";

const ApexChart = dynamic(() => import("react-apexcharts"), { ssr: false });

const colors = ['#4682b4', '#ff8c00', '#228b22', '#ff0000'];

const GroupChart = ({ chartConfig }) => {
  console.log("GroupChart config:", chartConfig);
  
  // if (!chartConfig || !Array.isArray(chartConfig.data.data) || chartConfig.data.data.length === 0) {
  //   return <div>No chart data available</div>;
  // }

  const barChartData = chartConfig.data.bar_chart_data;

  const chartMeta = {
    title: barChartData.title || "Portofolio Performance",
    description: barChartData.description || "",
    statistics: barChartData.statistics,
    exchange: barChartData.exchange || "NMS",
    x_axis_display_name: "Date",
    y_axis_display_name: "Indexed Value"
  };

  const xCategories = [...new Set(barChartData.map(d => d.date))];
  const barDimensions =  [...new Set(barChartData.map(item => item.dimension))];

  // Prepare series for ApexCharts
  const lineSeries = barDimensions.map((dim, i) => ({
    name: dim,
    type: 'line',
    data: xCategories.map(date => {
      const found = barChartData.find(d => d.dimension === dim && d.last_date === date);
      return found ? found.portfolio_return : 0;
    }),
    color: colors[i % colors.length],
  }));

  const barSeries = barDimensions.map((dim, i) => ({
    name: `${dim} Returns`,
    type: 'column',
    data: xCategories.map(date => {
      const found = barChartData.find(d => d.dimension === dim && d.last_date === date);
      return found ? found.portfolio_return : 0;
    }),
    color: colors[i % colors.length],
  }));

  // Fix: assign colors array to options.colors so each series gets a unique color
  const series = [...lineSeries, ...barSeries];

  const options = {
    chart: {
      height: '100%',
      width: '100%',
      type: 'line',
      stacked: false,
      toolbar: { show: false },
      background: 'transparent',
      fontFamily: 'inherit',
    },
    colors: [...colors, ...colors], // ensure enough colors for all series
    stroke: {
      width: [3, 3, 3, 3, 0, 0, 0, 0], // 4 lines, 4 bars (adjust if more series)
      curve: 'smooth',
    },
    plotOptions: {
      bar: {
        columnWidth: '60%',
        borderRadius: 2,
        opacity: 0.3,
      },
    },
    dataLabels: {
      enabled: false,
    },
    xaxis: {
      categories: xCategories,
      type: 'datetime',
      labels: {
        rotate: -45,
        style: { colors: '#fff' },
        datetimeFormatter: {
          year: 'yyyy',
          month: "yyyy-MM",
          day: 'yyyy-MM-dd',
        },
      },
      title: { text: chartMeta.x_axis_display_name, style: { color: '#fff' } },
      axisBorder: { color: '#fff' },
      axisTicks: { color: '#fff' },
    },
    yaxis: [
      {
        seriesName: 'Indexed',
        title: { text: chartMeta.y_axis_display_name, style: { color: '#fff' } },
        labels: { style: { colors: '#fff' } },
        min: 0,
      },
      {
        opposite: true,
        seriesName: 'Returns',
        title: { text: 'Return (%)', style: { color: '#fff' } },
        labels: { style: { colors: '#fff' } },
        min: -15,
        max: 15,
      }
    ],
    legend: {
      show: false, // Hide built-in ApexCharts legend
    },
    tooltip: {
      shared: true,
      intersect: false,
      x: { format: 'yyyy-MM' },
    },
    grid: {
      borderColor: '#444',
      strokeDashArray: 3,
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
    },
    title: {
      text: `${barDimensions.join(', ')} — Indexed Performance + Returns`,
      align: 'center',
      style: { color: '#fff', fontSize: '18px' },
    },
  };

  return (
    <div className="bg-gray-800 p-2 rounded-lg shadow mx-2 mb-2 border border-white h-full flex flex-col">
      <div className="text-center mt-1">
        <h3 className="text-sm font-bold text-white">{chartMeta.title}</h3>
        <p className="text-[#FFE600] text-xs font-mediun">{chartMeta.description}</p>
      </div>
      <div className="flex justify-end mb-2">
        {/* <button className="bg-gray-700 text-gray-300 px-3 py-1 rounded text-xs">
          Range: 3mo
        </button> */}
      </div>
      <div className="flex flex-row justify-between w-full">
        <div className="flex flex-row items-center space-x-2">
          {barDimensions.map((dim, i) => (
            <span key={dim} className="flex items-center text-xs text-white">
              <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 6, background: colors[i % colors.length], marginRight: 4 }}></span>
              {dim}
            </span>
          ))}
        </div>
        <div className="flex flex-row items-center space-x-2">
          {barDimensions.map((dim, i) => (
            <span key={dim + '-returns'} className="flex items-center text-xs text-white">
              <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 6, background: colors[i % colors.length], marginRight: 4, opacity: 0.3 }}></span>
              {dim} Returns
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center mt-2 w-full h-full">
        <ApexChart options={options} series={series} type="line" height="100%" width="100%" style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
};

export default GroupChart;
