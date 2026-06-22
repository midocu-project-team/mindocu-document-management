import { createTheme } from '@mui/material/styles';

/**
 * App-wide MUI theme with light + dark color schemes.
 *
 * Uses MUI's CSS-variables engine with a class-based selector: the active
 * scheme is applied as a `.light` / `.dark` class on <html> (toggled via
 * `useColorScheme`). The same `.dark` class drives the dark overrides for the
 * hand-written workspace styles in `components/workspace/workspace.css`, so the
 * MUI surfaces and the CSS-var-based workspace stay in sync.
 *
 * Brand colour is the indigo used across the upload pipeline; in dark mode it is
 * lightened for sufficient contrast against dark surfaces.
 */
export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'class' },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: '#1a237e' },
        background: { default: '#f4f5f7', paper: '#ffffff' },
        divider: '#e0e0e0',
        text: { primary: '#1e2430', secondary: '#5f6b7a' },
      },
    },
    dark: {
      palette: {
        primary: { main: '#7986cb' },
        background: { default: '#131419', paper: '#1e2026' },
        divider: '#2e313b',
        text: { primary: '#e6e8ee', secondary: '#9aa3b5' },
      },
    },
  },
  shape: { borderRadius: 8 },
});
