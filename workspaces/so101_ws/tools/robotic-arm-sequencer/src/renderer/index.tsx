console.log('=== RENDERER INDEX.TSX STARTED ===');
console.log('Time:', new Date().toISOString());

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/index.css';

console.log('=== IMPORTS COMPLETED ===');


const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);
root.render(<App />);