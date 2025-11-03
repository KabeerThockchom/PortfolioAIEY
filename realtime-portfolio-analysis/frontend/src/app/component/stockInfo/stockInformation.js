import React from "react";

const StockInformation = () => {
    return(
        <div>
            <div className="bg-gray-800 px-4 rounded-xl shadow-lg">
        <h2 className="text-xl font-semibold mb-4">Stock Information</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div className="bg-gray-700 px-2 rounded">Current Price<br /><strong>$208.78</strong></div>
          <div className="bg-gray-700 px-2 rounded text-red-400">Change<br /><strong>$-36.09 (-14.74%)</strong></div>
          <div className="bg-gray-700 px-2 rounded">Day Range<br /><strong>$204.26 - $209.48</strong></div>
          <div className="bg-gray-700 px-2 rounded">52 Week Range<br /><strong>$169.21 - $260.10</strong></div>
          <div className="bg-gray-700 px-2 rounded">Volume<br /><strong>45,104,929</strong></div>
          <div className="bg-gray-700 px-2 rounded">Previous Close<br /><strong>$244.87</strong></div>
        </div>
        <div className="mt-4 text-center bg-gray-700 inline-block px-3 py-1 rounded-full text-sm">
          Exchange: NMS
        </div>
      </div>
        </div>
    )
}

export default StockInformation;