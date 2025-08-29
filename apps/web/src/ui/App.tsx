import { Routes, Route, Link, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Features from './pages/Features';

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <Link to="/" className="brand">Discarr</Link>
          <nav className="nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/features">Features</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          </nav>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/features" element={<Features />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
