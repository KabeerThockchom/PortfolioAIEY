import React from "react";
import {
  Container,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";

// Accept stockTableData as a prop instead of lastMessage
const StockTable = ({ stockTableData }) => {
  console.log("StockTable Data:", stockTableData);
  const tableData = stockTableData.table;
  const totalData = stockTableData.total;
  const getColor = (value) => (value >= 0 ? "green" : "red");
  return (
    <div>
      <Container>
        <Typography variant="h6" className="text-center text-white py-2 top-0 z-20 shadow">
          Portfolio Details
        </Typography>
        <TableContainer
          sx={{
            maxHeight: "100%",

            borderRadius: 2,
            overflow: "auto",
          }}
          component={Paper}
          className="max-h-full bg-gray-800 overflow-auto"
        >
          <Table
            sx={{
              "& .MuiTableCell-root": {
                color: "#ffffff",
              },
            }}
            className="bg-gray-900"
          >
            <TableHead>
              <TableRow>
                {/* Table headers */}
                <TableCell className="font-bold text-xs">
                  <strong>Account Number</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Ticker</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Asset Name</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Investment Type</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Concentration</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Quantity</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Avg. Cost</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Purchase Cost</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Current Price</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>Current Value</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>P&amp;L</strong>
                </TableCell>
                <TableCell className="font-bold text-xs">
                  <strong>% Change</strong>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tableData.map((row, index) => (
                <TableRow key={index}>
                  <TableCell align="center">{row["Account Number"]}</TableCell>
                  <TableCell align="center">{row["Ticker"]}</TableCell>
                  <TableCell align="center">{row["Asset Name"]}</TableCell>
                  <TableCell align="center">{row["Investment Type"]}</TableCell>
                  <TableCell align="center">{row["Concentration"]}</TableCell>
                  <TableCell align="center">{row["Quantity"]}</TableCell>
                  <TableCell align="center">{row["Avg. Cost"]}</TableCell>
                  <TableCell align="center">{row["Purchase Cost"]}</TableCell>
                  <TableCell sx={{ color: "#193cb8 !important" }} align="center">
                    {row["Current Price"]}
                  </TableCell>
                  <TableCell sx={{ color: "#193cb8 !important" }} align="center">
                    {row["Current Value"]}
                  </TableCell>
                  <TableCell
                    align="center"
                    style={{ color: getColor(row["P&L"]) }}
                  >
                    {row["P&L"]}
                  </TableCell>
                  <TableCell
                    align="center"
                    style={{ color: getColor(row["Percentage Change"]) }}
                  >
                    {row["Percentage Change"]}
                  </TableCell>
                </TableRow>
              ))}
              <TableRow key="total">
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center">
                  <strong>{totalData.total_purchase_cost}</strong>
                </TableCell>
                <TableCell align="center"></TableCell>
                <TableCell align="center">
                  <strong>{totalData.total_current_value}</strong>
                </TableCell>
                <TableCell
                  align="center"
                  style={{ color: getColor(totalData.total_pnl) }}
                >
                  <strong>{totalData.total_pnl}</strong>
                </TableCell>
                <TableCell
                  align="center"
                  strong
                  style={{ color: getColor(totalData.total_percentage_change) }}
                >
                  <strong>{totalData.total_percentage_change}</strong>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      </Container>
    </div>
  );
};

export default StockTable;
