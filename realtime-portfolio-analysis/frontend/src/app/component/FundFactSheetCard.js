import React from "react";

export function FundFactSheetCard({ fund }) {
  if (!fund || !fund.data) return null;
  return (
    <div className="rounded-xl bg-gray-900	bg-gray-800 border-gray-700	bg-gray-800 border-b border-gray-700	bg-gray-700 border border-gray-600 border border-slate-700 p-4 shadow flex-1 min-w-[240px] max-w-md">
      <div className="text-lg font-semibold text-slate-100 mb-2">Fund Documents</div>
      <a
        href={fund.data.file_link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center text-blue-400 hover:underline"
      >
        <span>{fund.data.message}</span>
        <svg className="w-5 h-5 ml-2 text-blue-300" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </a>
    </div>
  );
}
