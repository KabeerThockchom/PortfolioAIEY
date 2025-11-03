import React from "react";

const ChartInformation = ({ statistics, exchange }) => {
  if (!statistics) {
    return <div>Loading ho raha hai from chart info...</div>;
  }
  return (
    <div className="bg-gray-800 p-2 rounded-lg shadow m-1">
      <h2 className="text-xs font-semibold mb-1 text-white">Stock Information</h2>
      <div className="grid grid-cols-2 gap-1 text-xs text-white">
        <div className="bg-gray-700 p-1 rounded">
          Portfolio Return (Jan)
          <br />
          <strong>{statistics["Portfolio Return (Jan)"]}</strong>
        </div>
        <div className="bg-gray-700 p-1 rounded">
          Benchmark Return (Jan)
          <br />
          <strong>{statistics["Benchmark Return (Jan)"]}</strong>
        </div>
        <div className="bg-gray-700 p-1 rounded">
          Highest Monthly Return
          <br />
          <strong>{statistics["Highest Monthly Return"]}</strong>
        </div>
        <div className="bg-gray-700 p-1 rounded">
          Lowest Monthly Return
          <br />
          <strong>{statistics["Lowest Monthly Return"]}</strong>
        </div>
        <div className="bg-gray-700 p-1 rounded">
         Average Portfolio Return
          <br />
          <strong>{statistics["Average Portfolio Return"]}</strong>
        </div>
        <div className="bg-gray-700 p-1 rounded">
          Average Benchmark Return
          <br />
          <strong>{statistics["Average Benchmark Return"]}</strong>
        </div>
      </div>
      <div className="mt-2 text-center bg-gray-700 inline-block px-2 py-0.5 rounded-full text-xs">
        Exchange: {exchange || "NMS"}
      </div>
    </div>
  );
};

export default ChartInformation;
