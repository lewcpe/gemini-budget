
import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Receipt, 
  Wallet, 
  Tags, 
  Inbox, 
  Settings as SettingsIcon,
  Menu,
  X,
  TrendingUp,
  FileUp,
  Activity,
  Store
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Accounts from './pages/Accounts';
import Categories from './pages/Categories';
import Merchants from './pages/Merchants';
import Proposals from './pages/Proposals';
import Settings from './pages/Settings';
import { apiService } from './apiService';

interface NavLinkProps {
  to: string;
  icon: any;
  children: React.ReactNode;
  active: boolean;
}

const NavLink: React.FC<NavLinkProps> = ({ to, icon: Icon, children, active }) => (
  <Link
    to={to}
    className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
      active 
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-100 font-semibold scale-[1.02]' 
        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
    }`}
  >
    <Icon size={20} />
    <span>{children}</span>
  </Link>
);

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    const checkStatus = async () => {
      try {
        await apiService.checkStatus();
        setApiOnline(true);
      } catch {
        setApiOnline(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleMobileMenu = () => setIsMobileMenuOpen(!isMobileMenuOpen);

  return (
    <div className="min-h-screen flex bg-gray-50 text-gray-900 selection:bg-blue-100">
      <aside className="hidden md:flex flex-col w-72 bg-white border-r border-gray-100 sticky top-0 h-screen p-6">
        <div className="flex items-center space-x-3 mb-10 px-2">
          <div className="bg-blue-600 p-2.5 rounded-2xl shadow-xl shadow-blue-100">
            <TrendingUp className="text-white" size={24} />
          </div>
          <h1 className="text-xl font-black tracking-tight text-gray-900">Gemini Budget</h1>
        </div>
        
        <nav className="flex-1 space-y-1.5">
          <NavLink to="/" icon={LayoutDashboard} active={location.pathname === '/'}>Dashboard</NavLink>
          <NavLink to="/transactions" icon={Receipt} active={location.pathname === '/transactions'}>Transactions</NavLink>
          <NavLink to="/accounts" icon={Wallet} active={location.pathname === '/accounts'}>Accounts</NavLink>
          <NavLink to="/categories" icon={Tags} active={location.pathname === '/categories'}>Categories</NavLink>
          <NavLink to="/merchants" icon={Store} active={location.pathname === '/merchants'}>Merchants</NavLink>
          <NavLink to="/proposals" icon={Inbox} active={location.pathname === '/proposals'}>AI Inbox</NavLink>
          <NavLink to="/settings" icon={SettingsIcon} active={location.pathname === '/settings'}>Settings</NavLink>
        </nav>

        <div className="mt-auto space-y-4">
          <div className="bg-gray-50 rounded-2xl p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Activity size={16} className="text-gray-400" />
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">API Health</span>
            </div>
            {apiOnline === null ? (
              <div className="w-2 h-2 rounded-full bg-gray-300 animate-pulse"></div>
            ) : apiOnline ? (
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            ) : (
              <div className="w-2 h-2 rounded-full bg-rose-500"></div>
            )}
          </div>
          
          <Link 
            to="/proposals" 
            className="flex items-center justify-center space-x-2 w-full bg-gray-900 text-white py-3.5 px-4 rounded-2xl font-bold shadow-xl shadow-gray-200 hover:bg-black transition-all transform active:scale-[0.98]"
          >
            <FileUp size={18} />
            <span>Upload Receipt</span>
          </Link>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden flex items-center justify-between p-4 bg-white border-b border-gray-100">
          <div className="flex items-center space-x-2">
            <TrendingUp className="text-blue-600" size={24} />
            <span className="font-black text-lg tracking-tight">Gemini Budget</span>
          </div>
          <button onClick={toggleMobileMenu} className="p-2 text-gray-500">
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </header>

        {isMobileMenuOpen && (
          <div className="md:hidden fixed inset-0 z-50 bg-white p-6 animate-in fade-in zoom-in duration-200">
             <div className="flex justify-between items-center mb-8">
                <span className="font-black text-xl">Menu</span>
                <button onClick={toggleMobileMenu} className="p-2"><X size={24} /></button>
             </div>
            <nav className="space-y-3">
              <NavLink to="/" icon={LayoutDashboard} active={location.pathname === '/'} >Dashboard</NavLink>
              <NavLink to="/transactions" icon={Receipt} active={location.pathname === '/transactions'}>Transactions</NavLink>
              <NavLink to="/accounts" icon={Wallet} active={location.pathname === '/accounts'}>Accounts</NavLink>
              <NavLink to="/categories" icon={Tags} active={location.pathname === '/categories'}>Categories</NavLink>
              <NavLink to="/merchants" icon={Store} active={location.pathname === '/merchants'}>Merchants</NavLink>
              <NavLink to="/proposals" icon={Inbox} active={location.pathname === '/proposals'}>AI Inbox</NavLink>
              <NavLink to="/settings" icon={SettingsIcon} active={location.pathname === '/settings'}>Settings</NavLink>
            </nav>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-4 md:p-12 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/merchants" element={<Merchants />} />
          <Route path="/proposals" element={<Proposals />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppLayout>
    </Router>
  );
};

export default App;
