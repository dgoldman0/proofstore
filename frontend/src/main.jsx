import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

// Entry point for the React application. This file mounts the root
// component onto the #root element provided in index.html.

const rootEl = document.getElementById('root');
createRoot(rootEl).render(<App />);