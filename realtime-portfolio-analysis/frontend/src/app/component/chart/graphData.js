import React from "react";

const GraphData = () => {
  return (
    <div className="bg-gray-800 px-4 rounded-xl shadow-lg">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold mb-2">Stock Visualization</h2>
          <span className="bg-gray-700 px-2 py-1 rounded text-sm">
            Interval: 1wk
          </span>
        </div>
        <div>
          <select className="bg-gray-700 px-2 py-1 rounded text-sm text-white">
            <option>Price</option>
            <option>Volume</option>
          </select>
          <span className="ml-2 bg-gray-700 px-2 py-1 rounded text-sm">
            Range: 3mo
          </span>
        </div>
      </div>
    </div>
  );
};

export default GraphData;
