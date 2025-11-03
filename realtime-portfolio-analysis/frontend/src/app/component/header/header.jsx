import React, { useState, useEffect } from "react";
import {
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  Switch,
} from "@mui/material";
import Logout from "@mui/icons-material/Logout";
import AccountBoxIcon from "@mui/icons-material/AccountBox";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";

export default function Header({
  micTemplate,
  onLogout,
  changePipeline,
  isRealtime,
  setIsRealtime,
  cashBalance,
  loadingCash,
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const cashColor = cashBalance < 100 ? "text-red-500" : "text-green-500";

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    onLogout();
    handleClose();
  };

  const handleResetDb = async () => {
    handleClose();
    let userId = null;
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const userObj = JSON.parse(userStr);
        userId = userObj.data.user_id;
      }
    } catch (e) {
      userId = null;
    }
    if (!userId) {
      alert("User ID not found!");
      return;
    }
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/reset_db?user_id=${userId}`,
        // `https://rtpa-be.azurewebsites.net/api/reset_db?user_id=${userId}`,
        {
          method: "GET",
          headers: { Accept: "application/json" },
        }
      );
      if (!response.ok) {
        const errorData = await response.json();
        alert(`Reset failed: ${errorData.detail || response.statusText}`);
        return;
      }
      await response.json();
      // Optionally: refresh state/UI here
    } catch (error) {
      alert(`Reset failed: ${error.message}`);
    }
  };

  const handleSwitchChange = (event) => {
    setIsRealtime(event.target.checked);
  };

  return (
    <header className="fixed top-0 left-0 w-full h-16 z-30 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 shadow-md flex items-center px-8">
      <div className="flex items-center gap-3">
        <span className="block w-2 h-8 rounded-full bg-gradient-to-b from-yellow-400 to-yellow-600"></span>
        <span className="text-2xl font-bold tracking-tight text-slate-100 drop-shadow">
          EY Prometheus
        </span>
      </div>
      <div className="flex items-center ml-20 flex-1">
        {micTemplate && micTemplate()}
      </div>
      <div className="flex items-center gap-4">
        <div className={`text-lg font-bold text-white drop-shadow`}>
          Cash available to Trade:{" "}
          <span className={`text-lg font-bold ${cashColor} drop-shadow`}>
            {loadingCash
              ? "Loading..."
              : `$${cashBalance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          </span>
        </div>
        <IconButton
          onClick={handleClick}
          size="small"
          sx={{
            ml: 2,
            bgcolor: "rgb(30, 30, 30)",
            color: "white",
          }}
          aria-controls={open ? "account-menu" : undefined}
          aria-haspopup="true"
          aria-expanded={open ? "true" : undefined}
        >
          <Avatar sx={{ width: 32, height: 32 }}>
            <AccountBoxIcon sx={{ color: "white" }} />
          </Avatar>
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          id="account-menu"
          open={open}
          onClose={handleClose}
          slotProps={{
            paper: {
              elevation: 0,
              sx: {
                bgcolor: "rgb(30, 30, 30)",
                color: "white",
                overflow: "visible",
                filter: "drop-shadow(0px 2px 8px rgba(0,0,0,0.32))",
                mt: 1.5,
                "& .MuiAvatar-root": {
                  width: 32,
                  height: 32,
                  ml: -0.5,
                  mr: 1,
                },
                "&::before": {
                  content: '""',
                  display: "block",
                  position: "absolute",
                  top: 0,
                  right: 14,
                  width: 10,
                  height: 10,
                  bgcolor: "background.paper",
                  transform: "translateY(-50%) rotate(45deg)",
                  zIndex: 0,
                },
              },
            },
          }}
          transformOrigin={{ horizontal: "right", vertical: "top" }}
          anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        >
          <MenuItem
            onClick={(event) => {
              event.stopPropagation();
            }}
          >
            <ListItemIcon>
              <Switch
                checked={isRealtime}
                onChange={handleSwitchChange}
                sx={{
                  "& .MuiSwitch-switchBase.Mui-checked": {
                    color: "white",
                  },
                  "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                    bgcolor: "lightblue",
                  },
                }}
              />
            </ListItemIcon>
            Use Realtime
          </MenuItem>
          <MenuItem onClick={handleResetDb}>
            <ListItemIcon>
              <DeleteForeverIcon fontSize="small" sx={{ color: "white" }} />
            </ListItemIcon>
            Reset DB
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <Logout fontSize="small" sx={{ color: "white" }} />
            </ListItemIcon>
            Logout
          </MenuItem>
        </Menu>
      </div>
    </header>
  );
}

