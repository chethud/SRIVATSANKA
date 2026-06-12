import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { BrandProvider } from './context/BrandContext';
import { ThemeProvider } from './context/ThemeContext';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <BrandProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrandProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
);
