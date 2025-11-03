import React, { useRef, useState, useEffect } from "react";

const SidebarContent = ({ showSessionLogs, newsCards }) => {
  const containerRef = useRef(null);
  const [userScrolled, setUserScrolled] = useState(false);

  // Detect user scroll
  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    // If user is not at the bottom, set userScrolled to true
    const atBottom = el.scrollHeight - el.scrollTop === el.clientHeight;
    setUserScrolled(!atBottom);
  };

  // Scroll to bottom when sessionLogs change, unless user scrolled up
  useEffect(() => {
    const el = containerRef.current;
    if (!el || userScrolled) return;
    el.scrollTop = el.scrollHeight;
  }, [showSessionLogs, userScrolled]);
  
const examplePrompts = [
  "Show me my portfolio fund distribution by asset class",
  "Show me my portfolio fund distribution by sector",
  "show me portfolio value by sector and asset class",
  "show me fund distribution by sector and asset class",
  "can you show my the portfolio performance for last 1 year",
  "Can you benchmark my portfolio",

];


  return (
    <div className="flex flex-col gap-6 h-full pt-6">
      <div
        ref={containerRef}
        onScroll={handleScroll}
         className="flex-1 min-h-[460px] max-h-80 overflow-y-auto rounded-xl bg-slate-900/80 px-4 py-3 shadow-inner"

      >
        {showSessionLogs()}
      </div>
      <div>
        {newsCards?.query_type === "news" && (
          <div className="rounded-xl bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 border border-slate-700 p-4 shadow">
            <div className="text-lg font-semibold text-slate-100 mb-2">News</div>
            {newsCards.data.map((card, idx) => (
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
        )}
        {newsCards?.query_type === "fund_fact_sheet" && (
          <div className="rounded-xl bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 border border-slate-700 p-4 shadow">
            <div className="text-lg font-semibold text-slate-100 mb-2">Fund Documents</div>
            <a
              href={newsCards.data.file_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-blue-400 hover:underline"
            >
              <span>{newsCards.data.message}</span>
              <svg className="w-5 h-5 ml-2 text-blue-300" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
            </a>
          </div>
        )}
      </div>
     <div className="mt-auto pt-4">
        <div className="rounded-xl bg-slate-900/80 border border-slate-700 p-4 shadow-sm">
          <div className="flex items-center mb-3">
            <svg className="w-4 h-4 text-blue-400 mr-2" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 14h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8s-9-3.582-9-8 4.03-8 9-8 9 3.582 9 8z" />
            </svg>
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Example Prompts
            </span>
          </div>
          <ul className="flex flex-col gap-2">
            {examplePrompts.map((prompt, idx) => (
              <li
                key={idx}
                className="flex items-center group"
              >
                <span className="flex items-center  bg-gray-900	bg-gray-800 border-gray-700	bg-gray-800 border-b border-gray-700	bg-gray-700 border border-gray-600 group-hover:bg-blue-900 transition-colors text-slate-200 group-hover:text-blue-300 rounded-full px-4 py-2 text-xs font-medium shadow cursor-pointer w-full">
                  <svg className="w-3 h-3 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20"><circle cx="10" cy="10" r="10"/></svg>
                  {prompt}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    
    </div>
  );
};

export default SidebarContent;
