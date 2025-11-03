
import React from "react";

export default function PortfolioTradeForm({ trade }) {
  console.log(trade, "ccccccccccccc")
  const t = trade?.data || {};

  const show = (val) => (val !== undefined && val !== null && val !== "" ? val : "—");

  return (
    <div className="bg-gray-900 border border-gray-600 rounded-2xl p-5 w-full max-w-md shadow-lg mx-auto">
      <div
        type="button"
        className="w-full  text-white font-semibold py-2  transition"
      >
         Order Summary
      </div>
      <div className="w-full flex items-center justify-between mb-4">
  {t.order_status === "Placed" ? (
    <>
      <div className="text-green-400 font-semibold text-sm">Your order is successfully confirmed</div>
      <span className="text-xs px-2 py-1 rounded bg-green-900 text-green-300 border border-green-700 ml-2">Status: Placed</span>
    </>
  ) : t.order_status === "Under Review" ? (
    <>
      <div className="text-white font-semibold text-sm">Preview order</div>
      <span className="text-xs px-2 py-1 rounded bg-yellow-900 text-yellow-300 border border-yellow-700 ml-2">Status: Under Review</span>
    </>
  ) : (
    <>
      <div className="text-white font-semibold text-sm">—</div>
      <span className="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400 border border-gray-700 ml-2">Status: —</span>
    </>
  )}
</div>

      <div className="mb-4">
        <label className="block text-xs text-slate-400 mb-1">TRADE</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value={show(t.trade)}
          readOnly
        />
      </div>
      <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">ACCOUNT</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value={show(t.account)}
          readOnly
        />
      </div>
      <div className="mb-1 flex justify-between items-center">
        <span className="text-xs text-slate-400">Cash available to trade</span>
        <span className="text-slate-100 font-semibold">
          {t.cash_balance !== undefined && t.cash_balance !== null
            ? `$${t.cash_balance}`
            : "—"}
        </span>
      </div>
      <div className="text-xs text-slate-500 mb-2">
        {t.order_date ? `As of ${t.order_date}` : ""}
      </div>
      <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">SYMBOL</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value={show(t.symbol)}
          readOnly
        />
      </div>
      <div className="mb-2">
        <div className="flex items-end justify-between">
          <span className="text-base text-slate-100 font-semibold">
            {show(t.symbol === "AAPL" ? "Apple" : "")}
          </span>
          <span className="text-2xl font-bold text-slate-100">
            {t.unit_price !== undefined && t.unit_price !== null
              ? `$${t.unit_price}`
              : "—"}
          </span>
        </div>
        {/* <div className="flex text-xs text-slate-400 mt-1 gap-4">
          <span>Bid —</span>
          <span>Ask —</span>
          <span>Volume —</span>
        </div> */}
      </div>
      {/* <div className="mb-2 flex items-center gap-2">
        <input type="checkbox" className="accent-blue-500" disabled />
        <span className="text-xs text-slate-400">
          Extended hours trading:{" "}
          <span className="font-semibold text-slate-200">Off</span>
          <span className="text-slate-500 ml-1">Until 8:00 PM ET</span>
        </span>
      </div> */}
      <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">ACTION</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value={show(t.action)}
          readOnly
        />
      </div>
      <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">QUANTITY</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          type="number"
          value={show(t.quantity)}
          readOnly
        />
      </div>
      <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">ORDER TYPE</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value={show(t.order_type)}
          readOnly
        />
      </div>
      {/* <div className="mb-2">
        <label className="block text-xs text-slate-400 mb-1">TIME IN FORCE</label>
        <input
          className="w-full bg-gray-800 text-slate-100 rounded px-3 py-2 border border-gray-600 text-sm font-semibold focus:outline-none"
          value="—"
          readOnly
        />
      </div> */}
      <div className="flex justify-between items-center text-xs text-slate-400 mt-3 mb-4">
        <span>Estimated value</span>
        <span className="text-slate-100 font-semibold">
          {t.amount !== undefined && t.amount !== null
            ? `$${t.amount}`
            : "—"}
        </span>
      </div>
    </div>
  );
}
