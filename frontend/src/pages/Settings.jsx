import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Cpu, Globe, CheckCircle, XCircle, Loader2, Save, ExternalLink } from 'lucide-react';

const PROVIDER_PRESETS = [
  {
    label: 'OpenRouter — Free Tier (Testing)',
    provider: 'openrouter',
    keyPlaceholder: 'sk-or-v1-...',
    keyLink: 'https://openrouter.ai/keys',
    models: [
      { label: 'Gemini 2.5 Flash (Free)', value: 'openrouter/google/gemini-2.5-flash:free' },
      { label: 'Gemini 2.0 Flash Exp (Free)', value: 'openrouter/google/gemini-2.0-flash-exp:free' },
      { label: 'Llama 3.3 70B (Free)', value: 'openrouter/meta-llama/llama-3.3-70b-instruct:free' },
      { label: 'Qwen 2.5 72B (Free)', value: 'openrouter/qwen/qwen-2.5-72b-instruct:free' },
      { label: 'Mistral 7B (Free)', value: 'openrouter/mistralai/mistral-7b-instruct:free' },
    ],
  },
  {
    label: 'DeepSeek — Production (Very Cheap)',
    provider: 'deepseek',
    keyPlaceholder: 'sk-...',
    keyLink: 'https://platform.deepseek.com/api_keys',
    models: [
      { label: 'DeepSeek V3 (Chat)', value: 'deepseek/deepseek-chat' },
      { label: 'DeepSeek R1 (Reasoner)', value: 'deepseek/deepseek-reasoner' },
    ],
  },
  {
    label: 'Custom / Self-Hosted',
    provider: 'custom',
    keyPlaceholder: 'Your API key',
    keyLink: null,
    models: [
      { label: 'GPT-4o', value: 'openai/gpt-4o' },
      { label: 'Ollama (Llama 3)', value: 'ollama/llama3' },
    ],
  },
];

export default function Settings({ onSaved, initialConfigured }) {
  const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');

  const [providerIdx, setProviderIdx] = useState(0);
  const [modelText, setModelText] = useState('openrouter/google/gemini-2.5-flash:free');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [showKey, setShowKey] = useState(false);

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveResult, setSaveResult] = useState(null);  // { success, message }
  const [testResult, setTestResult] = useState(null);  // { success, message }
  const [existingMasked, setExistingMasked] = useState('');

  const preset = PROVIDER_PRESETS[providerIdx];

  // Load existing settings from backend
  useEffect(() => {
    fetch(`${backendUrl}/settings`)
      .then(r => r.json())
      .then(data => {
        if (data.api_key_configured) setExistingMasked(data.api_key_masked);
        if (data.model) {
          setModelText(data.model);
          // Auto-detect provider index based on model prefix
          if (data.model.startsWith('openrouter/')) {
            setProviderIdx(0);
          } else if (data.model.startsWith('deepseek/')) {
            setProviderIdx(1);
          } else {
            setProviderIdx(2);
          }
        }
        if (data.base_url) setBaseUrl(data.base_url);
      })
      .catch(() => {});
  }, []);

  const handleProviderChange = (idx) => {
    setProviderIdx(idx);
    const p = PROVIDER_PRESETS[idx];
    if (p.models.length > 0) {
      setModelText(p.models[0].value);
    }
    setTestResult(null);
    setSaveResult(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveResult(null);
    setTestResult(null);
    try {
      const res = await fetch(`${backendUrl}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey || existingMasked, // use current text, or fall back to masked (which backend replaces)
          model: modelText.trim(),
          base_url: baseUrl.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSaveResult({ success: true, message: 'Settings saved successfully!' });
        if (onSaved) onSaved();
      } else {
        setSaveResult({ success: false, message: data.detail || 'Save failed.' });
      }
    } catch (e) {
      setSaveResult({ success: false, message: 'Network error. Is the server running?' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${backendUrl}/settings/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey || existingMasked,
          model: modelText.trim(),
          base_url: baseUrl.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setTestResult({ success: true, message: `Connection test OK! Model replied: "${data.reply}"` });
      } else {
        setTestResult({ success: false, message: data.detail || 'Test connection failed.' });
      }
    } catch (e) {
      setTestResult({ success: false, message: 'Could not contact server.' });
    } finally {
      setTesting(false);
    }
  };

  const isButtonDisabled = (!apiKey.trim() && !existingMasked) || !modelText.trim();

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2.5 bg-blue-600/10 border border-blue-500/20 text-blue-400 rounded-xl">
          <SettingsIcon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">LLM Settings</h1>
          <p className="text-sm text-gray-400">Configure your AI provider and API key for audit memo generation.</p>
        </div>
      </div>

      {/* Existing key banner */}
      {existingMasked && !apiKey && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 bg-green-950/30 border border-green-700/40 rounded-xl text-green-300 text-sm">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>API key already configured: <code className="font-mono bg-green-950/40 px-2 py-0.5 rounded">{existingMasked}</code>. Enter a new key below to replace it.</span>
        </div>
      )}

      <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-6">

        {/* Provider selector */}
        <div>
          <label className="block text-sm font-semibold text-gray-300 mb-2">Provider</label>
          <div className="grid grid-cols-3 gap-2">
            {PROVIDER_PRESETS.map((p, i) => (
              <button
                key={i}
                onClick={() => handleProviderChange(i)}
                className={`text-center px-3 py-3 rounded-xl border text-xs font-semibold transition-all ${
                  providerIdx === i
                    ? 'bg-blue-600/10 border-blue-500/50 text-blue-300'
                    : 'bg-dark-900 border-dark-600 text-gray-400 hover:border-dark-500 hover:text-white'
                }`}
              >
                {p.provider === 'openrouter' ? 'OpenRouter' : p.provider === 'deepseek' ? 'DeepSeek' : 'Custom / Local'}
              </button>
            ))}
          </div>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
            <Key className="w-4 h-4" /> API Key
            {preset.keyLink && (
              <a href={preset.keyLink} target="_blank" rel="noopener noreferrer"
                className="ml-auto text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                Get key <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={existingMasked ? '••••••••••••••••' : preset.keyPlaceholder}
              className="w-full bg-dark-900 border border-dark-600 rounded-xl px-4 py-3 text-white text-sm font-mono focus:outline-none focus:border-blue-500 transition-colors pr-20"
            />
            <button
              onClick={() => setShowKey(v => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-300 font-semibold"
            >
              {showKey ? 'HIDE' : 'SHOW'}
            </button>
          </div>
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
            <Cpu className="w-4 h-4" /> Model Name
          </label>
          <input
            type="text"
            value={modelText}
            onChange={e => setModelText(e.target.value)}
            placeholder="e.g. openrouter/google/gemini-2.5-flash:free or deepseek/deepseek-chat"
            className="w-full bg-dark-900 border border-dark-600 rounded-xl px-4 py-3 text-white text-sm font-mono focus:outline-none focus:border-blue-500 transition-colors"
          />

          {/* Model preset pills */}
          {preset.models.length > 0 && (
            <div className="mt-2.5">
              <span className="text-[11px] text-gray-400 font-bold block mb-1.5">QUICK PRESETS:</span>
              <div className="flex flex-wrap gap-1.5">
                {preset.models.map(m => (
                  <button
                    key={m.value}
                    onClick={() => setModelText(m.value)}
                    className={`px-2.5 py-1 text-[11px] font-semibold border rounded-lg transition-colors ${
                      modelText === m.value
                        ? 'bg-blue-600/20 border-blue-500/40 text-blue-300'
                        : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-dark-600 hover:text-white'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Custom Base URL (only for Custom provider) */}
        {preset.provider === 'custom' && (
          <div>
            <label className="block text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
              <Globe className="w-4 h-4" /> Base URL <span className="text-gray-500 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
              placeholder="e.g. http://localhost:11434/v1"
              className="w-full bg-dark-900 border border-dark-600 rounded-xl px-4 py-3 text-white text-sm font-mono focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        )}

        {/* Feedback messages */}
        {saveResult && (
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm border ${
            saveResult.success
              ? 'bg-green-950/30 border-green-700/40 text-green-300'
              : 'bg-red-950/30 border-red-700/40 text-red-300'
          }`}>
            {saveResult.success ? <CheckCircle className="w-4 h-4 flex-shrink-0" /> : <XCircle className="w-4 h-4 flex-shrink-0" />}
            {saveResult.message}
          </div>
        )}
        {testResult && (
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm border ${
            testResult.success
              ? 'bg-green-950/30 border-green-700/40 text-green-300'
              : 'bg-red-950/30 border-red-700/40 text-red-300'
          }`}>
            {testResult.success ? <CheckCircle className="w-4 h-4 flex-shrink-0" /> : <XCircle className="w-4 h-4 flex-shrink-0" />}
            <span className="whitespace-pre-wrap">{testResult.message}</span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving || isButtonDisabled}
            className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl transition-all shadow-[0_4px_14px_rgba(37,99,235,0.3)] hover:shadow-[0_4px_20px_rgba(37,99,235,0.5)]"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            onClick={handleTest}
            disabled={testing || isButtonDisabled}
            className="flex items-center justify-center gap-2 px-5 py-3 bg-dark-700 hover:bg-dark-600 border border-dark-600 disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 hover:text-white font-semibold text-sm rounded-xl transition-all"
          >
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>
      </div>
    </div>
  );
}
