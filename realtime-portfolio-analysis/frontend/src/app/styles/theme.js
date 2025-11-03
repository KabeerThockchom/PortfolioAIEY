import { createTheme } from '@mui/material/styles';

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#ffe600',
      contrastText: '#1a1a24',
    },
    secondary: {
      main: '#1a1a24',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f6f6fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a24',
      secondary: '#747480',
    },
  },
  typography: {
    fontFamily: '"EYInterstate"',
  },
});

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#ffe600',
      contrastText: '#1a1a24',
    },
    secondary: {
      main: '#ffffff',
      contrastText: '#1a1a24',
    },
    background: {
      default: '#1a1a24',
      paper: '#2e2e38',
    },
    text: {
      primary: '#f6f6fa',
      secondary: '#c4c4cd',
    },
  },
  typography: {
    fontFamily: '"EYInterstate"',
  },
});