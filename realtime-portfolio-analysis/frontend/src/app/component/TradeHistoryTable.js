import React from "react";

export default function TradeHistoryTable({ allData }) {
  if (!Array.isArray(allData) || allData.length === 0) {
    return (
      <div className="text-slate-400 text-sm mb-4">No trade history available.</div>
    );
  }

  return (
    <div className="mb-6">
      <div className="text-base font-semibold text-slate-100 mb-2">Order History</div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs bg-gray-900 border border-gray-600 rounded-xl">
          <thead>
            <tr className="bg-gray-700 text-slate-300">
              <th className="px-3 py-2 font-semibold text-left">Order ID</th>
              <th className="px-3 py-2 font-semibold text-left">Status</th>
              <th className="px-3 py-2 font-semibold text-left">Type</th>
              <th className="px-3 py-2 font-semibold text-left">Symbol</th>
              {/* <th className="px-3 py-2 font-semibold text-left">Description</th> */}
              <th className="px-3 py-2 font-semibold text-left">Buy/Sell</th>
              <th className="px-3 py-2 font-semibold text-left">Qty</th>
              {/* <th className="px-3 py-2 font-semibold text-left">Unit Price</th> */}
              <th className="px-3 py-2 font-semibold text-left">Amount</th>
              
              <th className="px-3 py-2 font-semibold text-left">Order Date</th>
            </tr>
          </thead>
          <tbody>
            {allData.map((row) => (
              <tr key={row.order_id} className="border-t border-gray-600 ">
                <td className="px-3 py-2 text-white">{row.order_id ?? "—"}</td>
                    <td className="px-3 py-2">
                  <span className={
                    row.order_status === "Placed"
                      ? "text-green-400"
                      : row.order_status === "Under Review"
                      ? "text-yellow-300"
                      : row.order_status === "Cancelled"
                      ? "text-red-400"
                      : "text-slate-300"
                  }>
                    {row.order_status ?? "—"}
                  </span>
                </td>
                <td className="px-3 py-2 text-white">{row.order_type ?? "—"}</td>
                <td className="px-3 py-2 text-white">{row.symbol ?? "—"}</td>
                {/* <td className="px-3 py-2">{row.description ?? "—"}</td> */}
                <td className="px-3 py-2 text-white">{row.buy_sell ?? "—"}</td>
                <td className="px-3 py-2 text-white">{row.qty ?? "—"}</td>
                {/* <td className="px-3 py-2">{row.unit_price !== null && row.unit_price !== undefined ? `$${row.unit_price}` : "—"}</td> */}
                <td className="px-3 py-2 text-white">{row.amount !== null && row.amount !== undefined ? `$${row.amount}` : "—"}</td>
            
                <td className="px-3 py-2 text-white">
                  {row.order_date ? row.order_date.split("T")[0] : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}




