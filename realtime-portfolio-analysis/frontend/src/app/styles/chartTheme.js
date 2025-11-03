import colorPallete from "./linearColors.json";

const defaultApexOptions = {
  colors: colorPallete.chartThemeColors, // or colorPallete.colors
  theme: {
    mode: "dark",
    //palette: colorPallete.chartThemeColors,
    monochrome: {
      enabled: false,
    },
  },
  chart: {
    background: "#111827",
    toolbar: { show: true },
    fontFamily: '"EYInterstate", Arial, Helvetica, sans-serif',
  },
  title: {
    style: {
      fontSize: "16px",
      fontWeight: "bold",
    },
  },
  legend: {
    labels: { colors: "#e5e7eb" },
  },
  xaxis: {
    labels: { style: { colors: "#e5e7eb" } },
    axisBorder: { color: "#6b7280" },
    axisTicks: { color: "#6b7280" },
  },
  yaxis: {
    labels: { style: { colors: "#e5e7eb" } },
  },
  tooltip: {
    theme: "dark",
  },
  grid: {
    borderColor: "#4b5563",
    strokeDashArray: 4,
  },
};

export default defaultApexOptions;
