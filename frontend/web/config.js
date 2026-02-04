/**
 * Configuration file for Labeling Tool Web Frontend
 *
 * DEPLOYMENT INSTRUCTIONS:
 * 1. Copy the 'web' folder to client machines
 * 2. Edit this file to set the correct API server address
 * 3. Open index.html in browser
 *
 * Or just set API_BASE directly in index.html
 */

// Set your API server address here
// Examples:
//   - Same machine: 'http://localhost:8000/api'
//   - Local network: 'http://192.168.1.100:8000/api'
//   - Remote server: 'http://your-server.com:8000/api'

window.API_BASE = 'http://localhost:8000/api';

// Alternatively, leave this file empty and the app will auto-detect
// based on the current page's hostname (useful when served from same server)
