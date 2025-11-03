// import React from "react";
// import DonutChart from "./chart/donutChart";
// import StockTable from "../table/stockTable";
// import BenchmarkChart from "./chart/benchmarkChart";
// import StackBar from "./chart/stackBar";
// import RangeColumnChart from "./chart/rangeColumnChart";
// import { NewsCard } from "./NewsCard";
// import { FundFactSheetCard } from "./FundFactSheetCard";
// import PortfolioTradeForm from "./PortfolioTradeForm";
// import RiskAnalysisChart from "./chart/riskAnalysisChart";

// import TradeHistoryTable from "./TradeHistoryTable";

// import RAGContextWidget from "./RAGContextWidget";




// const ChatLayout = ({
//   chartConfig,
//   newsData,
//   fundFactSheetData,
//   tradeData,
//   ragData
// }) => {
 
//   const selectDisplayType = (chartConfig) => {
//     if (chartConfig) {
//       switch (chartConfig.query_type) {
//         case "portfolio_benchmark":
//           return <BenchmarkChart chartConfig={chartConfig} />;
//         case "relative_performance":
//           return <StackBar chartConfig={chartConfig} />;
//         case "aggregation_level_1":
//           return <DonutChart chartConfig={chartConfig.data} />;
//         case "aggregation_level_2":
//           return <DonutChart chartConfig={chartConfig.data} />;
//         case "user_portfolio":
//           return <StockTable stockTableData={chartConfig.data} />;
//         case "risk_analysis":
//           return <RiskAnalysisChart chartConfig={chartConfig} />;
//         case "returns_attribution":
//           return <RangeColumnChart chartConfig={chartConfig} />;
//         default:
//           return (
//             <div className="p-4 text-center text-slate-400">
//               No data available
//             </div>
//           );
//       }
//     }
//     return (
//       <div className="p-4 text-center text-slate-400">No data available</div>
//     );
//   };
//    console.log(ragData, "ccccccccccccccccccccccccccccdddddddddddddddddccccccccccccccccc")

//   return (
//     // <div className="flex-1 min-h-0 flex flex-col">
//     //   {selectDisplayType(chartConfig)}
//     //    <div className="flex flex-row gap-6 mt-6">
//     //     {newsData && <NewsCard news={newsData} />}
//     //     {fundFactSheetData && <FundFactSheetCard fund={fundFactSheetData} />}
//     //   </div>
//     //   {/* csmjdcbkjsdbckjsd */}
//     //   <div className="w-full max-w-md flex-shrink-0">
//     //    <PortfolioTradeForm />
//     //  </div>
//     // </div>

//     <div className="flex-1 min-h-0 flex flex-row gap-8">
//       {/* Left: Chart + News/Fund */}
//       <div className="flex-1 min-w-0 flex flex-col">
//         {selectDisplayType(chartConfig)}
//         <div className="flex flex-row gap-6 mt-6">
//           {newsData && <NewsCard news={newsData} />}
//           {fundFactSheetData && <FundFactSheetCard fund={fundFactSheetData} />}
//         </div>
//       </div>
//       {/* Right: Form */}
//       {/* <div className="w-72 mt-12 flex-shrink-0">
//         {tradeData && <PortfolioTradeForm trade={tradeData} />}
//       </div> */}
//       {/* <div className="w-72 mt-12 flex-shrink-0">
//   {tradeData?.all_data && <TradeHistoryTable allData={tradeData.all_data} />}
//   {tradeData && <PortfolioTradeForm trade={tradeData} />}
// </div> */}

// <div className="w-72 mt-12 flex-shrink-0">
//   {tradeData?.all_data && <TradeHistoryTable allData={tradeData.all_data} />}
//   {tradeData && <PortfolioTradeForm trade={tradeData} />}
//   {ragData && <RAGContextWidget ragContext={ragData.data} />}
// </div>

//     </div>
//     // <main className="ml-72 mt-16 flex-1 min-h-screen p-6 flex flex-col">
//     // <div className="flex-1 min-h-0 flex flex-row gap-8 bg-slate-900/80 shadow-xl rounded-2xl p-6">
//     //   {/* Left: ChatLayout */}
//     //   {/* <div className="flex-1 min-w-0 flex flex-col">
//     //     <ChatLayout
//     //       chartConfig={chartConfig}
//     //       newsData={newsData}
//     //       fundFactSheetData={fundFactSheetData}
//     //     />
//     //   </div> */}
//     //    <div className="flex-1 min-w-0 flex flex-col">
//     //       {newsData && <NewsCard news={newsData} />}
//     //       {fundFactSheetData && <FundFactSheetCard fund={fundFactSheetData} />}
//     //     </div>
//     //   {/* Right: Trade Form */}
//     //   <div className="w-full max-w-md flex-shrink-0">
//     //     <PortfolioTradeForm />
//     //   </div>
//     // </div>
//     // </main>
//   );
// };

// export default ChatLayout;




import React from "react";
import DonutChart from "./chart/donutChart";
import StockTable from "../table/stockTable";
import BenchmarkChart from "./chart/benchmarkChart";
import StackBar from "./chart/stackBar";
import RangeColumnChart from "./chart/rangeColumnChart";
import { NewsCard } from "./NewsCard";
import { FundFactSheetCard } from "./FundFactSheetCard";
import PortfolioTradeForm from "./PortfolioTradeForm";
import RiskAnalysisChart from "./chart/riskAnalysisChart";

import TradeHistoryTable from "./TradeHistoryTable";

import RAGContextWidget from "./RAGContextWidget";




const ChatLayout = ({
  chartConfig,
  newsData,
  fundFactSheetData,
  tradeData,
  ragData,
  ragResponse
}) => {
 
  const selectDisplayType = (chartConfig) => {
    if (chartConfig) {
      switch (chartConfig.query_type) {
        case "portfolio_benchmark":
          return <BenchmarkChart chartConfig={chartConfig} />;
        case "relative_performance":
          return <StackBar chartConfig={chartConfig} />;
        case "aggregation_level_1":
          return <DonutChart chartConfig={chartConfig.data} />;
        case "aggregation_level_2":
          return <DonutChart chartConfig={chartConfig.data} />;
        case "user_portfolio":
          return <StockTable stockTableData={chartConfig.data} />;
        case "risk_analysis":
          return <RiskAnalysisChart chartConfig={chartConfig} />;
        case "returns_attribution":
          return <RangeColumnChart chartConfig={chartConfig} />;
        default:
          return (
            <div className="p-4 text-center text-slate-400">
              No data available
            </div>
          );
      }
    }
    return (
      <div className="p-4 text-center text-slate-400">No data available</div>
    );
  };

  return (
  

//     <div className="flex-1 min-h-0 flex flex-row gap-8">
//       {/* Left: Chart + News/Fund */}
//       <div className="flex-1  flex flex-col">
//        <div className="w-full min-w-6xl min-h-6xl h-[700px]"> {selectDisplayType(chartConfig)}</div>
//         <div className="flex flex-row gap-6 mt-6">
//             {tradeData?.all_data && <TradeHistoryTable allData={tradeData.all_data} />}
//             {ragData && <RAGContextWidget ragContext={ragData.data} />}
          
//           {/* {fundFactSheetData && <FundFactSheetCard fund={fundFactSheetData} />} */}
//         </div>
//       </div>
    

// <div className="w-72 gap-2 flex-shrink-0">

//   {tradeData && <PortfolioTradeForm trade={tradeData} />}
//   <div className="mt-10">
//   {newsData && <NewsCard news={newsData} />}
//   </div>
  
// </div>

//     </div>

<div className="flex-1 min-h-0 flex flex-row gap-4">
  <div className="flex-1 min-w-0 flex flex-col">
      {/* {ragData && <RAGContextWidget ragContext={ragData.data} />} */}
    <div className="w-full min-h-[600px] flex-1 flex flex-col justify-start">
      {selectDisplayType(chartConfig)}
    </div>
    <div className="flex flex-row gap-6 mt-6">
      {tradeData?.all_data && <TradeHistoryTable allData={tradeData.all_data} />}
      {ragData && (
  <RAGContextWidget 
    ragContext={ragData.data} 
    ragmessage={ragResponse?.data?.["Answer from RAG"]} 
  />
)}
    </div>
  </div>

  <div className="flex flex-col gap-6 w-full max-w-xs flex-shrink-0 ">
    {tradeData && <PortfolioTradeForm trade={tradeData} />}
    {newsData && <NewsCard news={newsData} />}
     {fundFactSheetData && <FundFactSheetCard fund={fundFactSheetData} />}
  </div>
 
</div>
  );
};

export default ChatLayout;

 