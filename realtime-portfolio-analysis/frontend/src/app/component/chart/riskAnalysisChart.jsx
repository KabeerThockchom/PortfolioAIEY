//import BubbleChartStatic from "./bubleChart.json";
import { useEffect, useState } from "react";
import BubbleChart from "./bubbleChart";
import GaugeChart from "./gauageChart";

const RiskAnalysisChart = ({ chartConfig }) => {
  const [bubbleChartData, setBubbleChartData] = useState(null);
  const [gaugeChartData, setGaugeChartData] = useState(null);
  useEffect(() => {
    if (chartConfig && chartConfig.data) {
      setBubbleChartData(chartConfig);
      setGaugeChartData(chartConfig.data.gauge_chart);
    }
  }, [chartConfig]);
  return (  
    <div className="grid grid-rows-12 h-full">
      <div className="row-span-2 content-center">
        <GaugeChart chartConfig={gaugeChartData} />
      </div>
      <div className="row-span-10">
        <BubbleChart chartConfig={bubbleChartData} />
      </div>
    </div>
  );
};


export default RiskAnalysisChart;
