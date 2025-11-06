
import React, { useState } from "react";
import FundTransferModal from "./FundTransferModal";

export default function PortfolioTradeForm({ trade, userId, onCashBalanceUpdate }) {
  console.log(trade, "ccccccccccccc")
  const t = trade?.data || {};
  const [showTransferModal, setShowTransferModal] = useState(false);

  const show = (val) => (val !== undefined && val !== null && val !== "" ? val : "—");

  // Check if cash balance is insufficient for a buy order
  const isBuyOrder = t.action?.toLowerCase() === 'buy';
  const cashBalance = t.cash_balance || 0;
  const orderAmount = t.amount || 0;
  const isInsufficientFunds = isBuyOrder && cashBalance < orderAmount;
  const shortfall = isInsufficientFunds ? orderAmount - cashBalance : 0;

  const handleTransferSuccess = (data) => {
    // Notify parent component to refresh cash balance
    if (onCashBalanceUpdate) {
      onCashBalanceUpdate(data.new_cash_balance);
    }
    setShowTransferModal(false);
  };

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

      {/* Insufficient Funds Warning */}
      {isInsufficientFunds && t.order_status === "Under Review" && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <div className="text-sm font-semibold text-red-300 mb-1">
                Insufficient Funds
              </div>
              <div className="text-xs text-red-400 mb-2">
                You need ${shortfall.toFixed(2)} more to complete this trade.
              </div>
              <button
                onClick={() => setShowTransferModal(true)}
                className="text-xs font-semibold bg-red-700 hover:bg-red-600 text-white px-3 py-1.5 rounded transition"
              >
                Transfer Funds
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fund Transfer Modal */}
      <FundTransferModal
        open={showTransferModal}
        onClose={() => setShowTransferModal(false)}
        userId={userId}
        requiredAmount={shortfall}
        onTransferSuccess={handleTransferSuccess}
      />
    </div>
  );
}
