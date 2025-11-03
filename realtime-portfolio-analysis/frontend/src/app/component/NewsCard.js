import React from "react";

export function NewsCard({ news }) {
  if (!news || !news.data || !Array.isArray(news.data) || news.data.length === 0) return null;
  return (
    <div className="rounded-xl bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 border border-slate-700 p-4 shadow flex-1 min-w-[240px] max-w-md">
      <div className="text-lg font-semibold text-slate-100 mb-2">News</div>
      {news.data.map((card, idx) => (
        <div key={idx} className="border-b border-slate-700 pb-2 mb-2 last:border-b-0 last:pb-0 last:mb-0">
          <a
            href={card.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline"
          >
            {card.headline}
          </a>
        </div>
      ))}
    </div>
  );
}