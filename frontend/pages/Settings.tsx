
import React, { useState } from 'react';
import { getApiSettings, setApiSettings } from '../apiService';
import { Save, RefreshCw, CheckCircle2, Server, User, HelpCircle } from 'lucide-react';

const Settings: React.FC = () => {
  const current = getApiSettings();
  const [apiUrl, setApiUrl] = useState(current.apiUrl);
  const [userEmail, setUserEmail] = useState(current.userEmail);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const handleSaveConnection = (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('saving');
    setApiSettings(apiUrl, userEmail);
    setTimeout(() => {
      setStatus('saved');
      setTimeout(() => setStatus('idle'), 2000);
      window.location.reload();
    }, 600);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-12 animate-in slide-in-from-bottom-4 duration-500">
      <header>
        <h1 className="text-4xl font-black text-gray-900 tracking-tight">Settings</h1>
        <p className="text-gray-500 mt-2 font-medium">Configure your connection to the budget backend.</p>
      </header>

      <div className="bg-white rounded-[40px] border border-gray-100 shadow-xl p-10 space-y-10">
        <form onSubmit={handleSaveConnection} className="space-y-10">
          <div className="space-y-8">
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-gray-900 font-black">
                <Server size={20} className="text-blue-600" />
                <span className="text-lg">Endpoint</span>
              </div>
              <input className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={apiUrl} onChange={e => setApiUrl(e.target.value)} />
            </div>
            <div className="space-y-4">
              <div className="flex items-center space-x-2 text-gray-900 font-black">
                <User size={20} className="text-blue-600" />
                <span className="text-lg">User Email</span>
              </div>
              <input className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" type="email" value={userEmail} onChange={e => setUserEmail(e.target.value)} />
            </div>
          </div>
          <button type="submit" disabled={status !== 'idle'} className="w-full flex items-center justify-center space-x-3 bg-blue-600 text-white py-4 px-8 rounded-2xl font-black shadow-2xl shadow-blue-100 transition-all">
            {status === 'saving' ? <RefreshCw size={22} className="animate-spin" /> : status === 'saved' ? <CheckCircle2 size={22} /> : <Save size={22} />}
            <span>Save Configuration</span>
          </button>
        </form>
      </div>

      <div className="bg-gray-900 text-white rounded-[40px] p-8 shadow-2xl flex items-start space-x-4">
        <HelpCircle className="text-blue-400 shrink-0 mt-1" size={24} />
        <div>
          <h3 className="font-black text-lg mb-2">Sync Notice</h3>
          <p className="text-xs text-gray-400 leading-relaxed">Ensure your server allows the <code>X-Forwarded-Email</code> header to identify your account sessions.</p>
        </div>
      </div>
    </div>
  );
};

export default Settings;
