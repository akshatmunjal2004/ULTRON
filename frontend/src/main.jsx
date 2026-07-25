import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { AgentProvider } from './context/AgentContext';
import { ToastProvider } from './context/ToastContext';
import ToastContainer from './components/ToastContainer';
import './styles/globals.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <ToastProvider>
        <AgentProvider>
          <BrowserRouter>
            <App />
            <ToastContainer />
          </BrowserRouter>
        </AgentProvider>
      </ToastProvider>
    </ErrorBoundary>
  </StrictMode>,
);
