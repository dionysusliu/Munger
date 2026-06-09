import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cpu,
  Settings2,
  Palette,
  Database,
  Terminal,
  Check,
  Eye,
  EyeOff,
  Wifi,
  WifiOff,
  Download,
  Upload,
  Trash2,
  AlertTriangle,
  Moon,
  Sun,
  Monitor,
  RotateCcw,
  Clock,
  FolderOpen,
  Languages,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// --- Types ---

type TabId = 'llm' | 'system' | 'appearance' | 'data' | 'advanced';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { id: 'llm', label: 'LLM Models', icon: <Cpu className="size-[18px]" /> },
  { id: 'system', label: 'System', icon: <Settings2 className="size-[18px]" /> },
  { id: 'appearance', label: 'Appearance', icon: <Palette className="size-[18px]" /> },
  { id: 'data', label: 'Data', icon: <Database className="size-[18px]" /> },
  { id: 'advanced', label: 'Advanced', icon: <Terminal className="size-[18px]" /> },
];

// --- Animation variants ---

const tabContentVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

const tabContentTransition = {
  duration: 0.2,
  ease: [0.4, 0, 0.2, 1] as [number, number, number, number],
};

// --- Card wrapper ---

function SettingCard({ title, children, className }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn('rounded-xl border p-5', className)}
      style={{
        background: '#14100D',
        borderColor: 'rgba(120, 53, 15, 0.12)',
        boxShadow: 'inset 0 1px 0 rgba(251,191,36,0.04)',
      }}
    >
      {title && <h3 className="text-[15px] font-semibold text-[#EDE4D3] mb-4">{title}</h3>}
      {children}
    </div>
  );
}

// --- Toggle Switch ---

function Toggle({ checked, onChange, label: _label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  void _label;
  return (
    <button
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors',
        checked ? 'bg-[#D97706]' : 'bg-[#78350F40]'
      )}
    >
      <span
        className={cn(
          'inline-block size-3.5 rounded-full bg-white transition-transform',
          checked ? 'translate-x-[calc(100%-2px)]' : 'translate-x-0.5'
        )}
      />
    </button>
  );
}

// --- Main Component ---

export default function Settings() {
  const [activeTab, setActiveTab] = useState<TabId>('llm');

  // LLM state
  const [defaultProvider, setDefaultProvider] = useState<'ollama' | 'openai' | 'anthropic'>('ollama');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState('llama3.2');
  const [openaiKey, setOpenaiKey] = useState('');
  const [openaiModel, setOpenaiModel] = useState('gpt-4o');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [anthropicModel, setAnthropicModel] = useState('claude-3-5-sonnet-20241022');
  const [showOpenAIKey, setShowOpenAIKey] = useState(false);
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [testStatus, setTestStatus] = useState<Record<string, 'idle' | 'testing' | 'success' | 'error'>>({
    ollama: 'idle',
    openai: 'idle',
    anthropic: 'idle',
  });

  // System state
  const [dataDir, setDataDir] = useState('/home/user/.munger/data');
  const [maxFileSize, setMaxFileSize] = useState(50);
  const [autoIngest, setAutoIngest] = useState(true);
  const [autoAnalyze, setAutoAnalyze] = useState(true);
  const [language, setLanguage] = useState('en');

  // Appearance state
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('dark');
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [density, setDensity] = useState<'compact' | 'default' | 'relaxed'>('default');

  // Data state
  const [storageUsed] = useState(3456); // MB
  const [storageTotal] = useState(10240); // MB
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Advanced state
  const [debugMode, setDebugMode] = useState(false);
  const [logLevel, setLogLevel] = useState('info');
  const [apiTimeout, setApiTimeout] = useState(60);
  const [maxConcurrent, setMaxConcurrent] = useState(3);

  // --- Handlers ---

  const handleTestConnection = useCallback((provider: string) => {
    setTestStatus((prev) => ({ ...prev, [provider]: 'testing' }));
    setTimeout(() => {
      setTestStatus((prev) => ({ ...prev, [provider]: Math.random() > 0.2 ? 'success' : 'error' }));
    }, 1500);
  }, []);

  const storagePercent = Math.round((storageUsed / storageTotal) * 100);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'llm':
        return (
          <motion.div
            key="llm"
            variants={tabContentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={tabContentTransition}
            className="max-w-[640px] space-y-5"
          >
            {/* Provider Selection */}
            <SettingCard title="Model Provider">
              <div className="space-y-3">
                {/* Ollama */}
                <div
                  className={cn(
                    'relative rounded-lg border p-4 cursor-pointer transition-all',
                    defaultProvider === 'ollama'
                      ? 'border-[#D97706] shadow-[0_0_20px_rgba(251,191,36,0.08)]'
                      : 'border-[#78350F20] hover:border-[#78350F50]'
                  )}
                  onClick={() => setDefaultProvider('ollama')}
                >
                  {defaultProvider === 'ollama' && (
                    <div className="absolute top-3 right-3 size-5 rounded-full bg-[#D97706] flex items-center justify-center">
                      <Check className="size-3 text-[#14100D]" />
                    </div>
                  )}
                  <div className="flex items-start gap-3">
                    <div
                      className={cn(
                        'size-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center',
                        defaultProvider === 'ollama' ? 'border-[#D97706]' : 'border-[#78350F]'
                      )}
                    >
                      {defaultProvider === 'ollama' && <div className="size-2 rounded-full bg-[#D97706]" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[#EDE4D3]">Ollama (Local)</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#65A30D15] text-[#65A30D] font-mono">Local</span>
                      </div>
                      <p className="text-[12px] text-[#7A6B5A] mt-0.5">Run models locally on your machine</p>

                      <div className="mt-3 space-y-2">
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">Base URL</label>
                          <input
                            type="text"
                            value={ollamaUrl}
                            onChange={(e) => setOllamaUrl(e.target.value)}
                            className="w-full h-8 px-2.5 text-xs rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                            style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">Model</label>
                          <select
                            value={ollamaModel}
                            onChange={(e) => setOllamaModel(e.target.value)}
                            className="w-full h-8 px-2.5 text-xs rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                            style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="llama3.2">Llama 3.2</option>
                            <option value="llama3.1">Llama 3.1</option>
                            <option value="mistral">Mistral</option>
                            <option value="codellama">CodeLlama</option>
                            <option value="phi4">Phi-4</option>
                          </select>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleTestConnection('ollama'); }}
                          className="flex items-center gap-1.5 h-7 px-3 rounded-md text-[11px] font-medium border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all mt-2"
                          style={{ borderColor: '#78350F40' }}
                        >
                          {testStatus.ollama === 'testing' && <span className="animate-spin size-3 border border-[#B8A88A] border-t-transparent rounded-full" />}
                          {testStatus.ollama === 'success' && <Wifi className="size-3 text-[#65A30D]" />}
                          {testStatus.ollama === 'error' && <WifiOff className="size-3 text-[#B91C1C]" />}
                          {testStatus.ollama === 'idle' && <Wifi className="size-3" />}
                          Test Connection
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* OpenAI */}
                <div
                  className={cn(
                    'relative rounded-lg border p-4 cursor-pointer transition-all',
                    defaultProvider === 'openai'
                      ? 'border-[#D97706] shadow-[0_0_20px_rgba(251,191,36,0.08)]'
                      : 'border-[#78350F20] hover:border-[#78350F50]'
                  )}
                  onClick={() => setDefaultProvider('openai')}
                >
                  {defaultProvider === 'openai' && (
                    <div className="absolute top-3 right-3 size-5 rounded-full bg-[#D97706] flex items-center justify-center">
                      <Check className="size-3 text-[#14100D]" />
                    </div>
                  )}
                  <div className="flex items-start gap-3">
                    <div
                      className={cn(
                        'size-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center',
                        defaultProvider === 'openai' ? 'border-[#D97706]' : 'border-[#78350F]'
                      )}
                    >
                      {defaultProvider === 'openai' && <div className="size-2 rounded-full bg-[#D97706]" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[#EDE4D3]">OpenAI</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#7C6BFF15] text-[#7C6BFF] font-mono">Cloud</span>
                      </div>
                      <p className="text-[12px] text-[#7A6B5A] mt-0.5">GPT-4o and GPT-4o-mini models</p>

                      <div className="mt-3 space-y-2">
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">API Key</label>
                          <div className="relative">
                            <input
                              type={showOpenAIKey ? 'text' : 'password'}
                              value={openaiKey}
                              onChange={(e) => setOpenaiKey(e.target.value)}
                              placeholder="sk-..."
                              className="w-full h-8 pl-2.5 pr-8 text-xs rounded-md border bg-transparent text-[#EDE4D3] placeholder-[#7A6B5A] outline-none focus:border-[#D97706] transition-colors font-mono"
                              style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                              onClick={(e) => e.stopPropagation()}
                            />
                            <button
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-[#7A6B5A] hover:text-[#EDE4D3]"
                              onClick={(e) => { e.stopPropagation(); setShowOpenAIKey(!showOpenAIKey); }}
                            >
                              {showOpenAIKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                            </button>
                          </div>
                        </div>
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">Model</label>
                          <select
                            value={openaiModel}
                            onChange={(e) => setOpenaiModel(e.target.value)}
                            className="w-full h-8 px-2.5 text-xs rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                            style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="gpt-4o">GPT-4o</option>
                            <option value="gpt-4o-mini">GPT-4o-mini</option>
                          </select>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleTestConnection('openai'); }}
                          className="flex items-center gap-1.5 h-7 px-3 rounded-md text-[11px] font-medium border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all mt-2"
                          style={{ borderColor: '#78350F40' }}
                        >
                          {testStatus.openai === 'testing' && <span className="animate-spin size-3 border border-[#B8A88A] border-t-transparent rounded-full" />}
                          {testStatus.openai === 'success' && <Wifi className="size-3 text-[#65A30D]" />}
                          {testStatus.openai === 'error' && <WifiOff className="size-3 text-[#B91C1C]" />}
                          {testStatus.openai === 'idle' && <Wifi className="size-3" />}
                          Test Connection
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Anthropic */}
                <div
                  className={cn(
                    'relative rounded-lg border p-4 cursor-pointer transition-all',
                    defaultProvider === 'anthropic'
                      ? 'border-[#D97706] shadow-[0_0_20px_rgba(251,191,36,0.08)]'
                      : 'border-[#78350F20] hover:border-[#78350F50]'
                  )}
                  onClick={() => setDefaultProvider('anthropic')}
                >
                  {defaultProvider === 'anthropic' && (
                    <div className="absolute top-3 right-3 size-5 rounded-full bg-[#D97706] flex items-center justify-center">
                      <Check className="size-3 text-[#14100D]" />
                    </div>
                  )}
                  <div className="flex items-start gap-3">
                    <div
                      className={cn(
                        'size-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center',
                        defaultProvider === 'anthropic' ? 'border-[#D97706]' : 'border-[#78350F]'
                      )}
                    >
                      {defaultProvider === 'anthropic' && <div className="size-2 rounded-full bg-[#D97706]" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[#EDE4D3]">Anthropic</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#C97B7B15] text-[#C97B7B] font-mono">Cloud</span>
                      </div>
                      <p className="text-[12px] text-[#7A6B5A] mt-0.5">Claude 3.5 Sonnet and Claude 3 Haiku</p>

                      <div className="mt-3 space-y-2">
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">API Key</label>
                          <div className="relative">
                            <input
                              type={showAnthropicKey ? 'text' : 'password'}
                              value={anthropicKey}
                              onChange={(e) => setAnthropicKey(e.target.value)}
                              placeholder="sk-ant-..."
                              className="w-full h-8 pl-2.5 pr-8 text-xs rounded-md border bg-transparent text-[#EDE4D3] placeholder-[#7A6B5A] outline-none focus:border-[#D97706] transition-colors font-mono"
                              style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                              onClick={(e) => e.stopPropagation()}
                            />
                            <button
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-[#7A6B5A] hover:text-[#EDE4D3]"
                              onClick={(e) => { e.stopPropagation(); setShowAnthropicKey(!showAnthropicKey); }}
                            >
                              {showAnthropicKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                            </button>
                          </div>
                        </div>
                        <div>
                          <label className="text-[11px] text-[#B8A88A] mb-1 block">Model</label>
                          <select
                            value={anthropicModel}
                            onChange={(e) => setAnthropicModel(e.target.value)}
                            className="w-full h-8 px-2.5 text-xs rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                            style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                            <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                          </select>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleTestConnection('anthropic'); }}
                          className="flex items-center gap-1.5 h-7 px-3 rounded-md text-[11px] font-medium border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all mt-2"
                          style={{ borderColor: '#78350F40' }}
                        >
                          {testStatus.anthropic === 'testing' && <span className="animate-spin size-3 border border-[#B8A88A] border-t-transparent rounded-full" />}
                          {testStatus.anthropic === 'success' && <Wifi className="size-3 text-[#65A30D]" />}
                          {testStatus.anthropic === 'error' && <WifiOff className="size-3 text-[#B91C1C]" />}
                          {testStatus.anthropic === 'idle' && <Wifi className="size-3" />}
                          Test Connection
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </SettingCard>

            {/* Save button */}
            <div className="flex justify-end pt-2">
              <button
                className="h-9 px-5 rounded-md text-sm font-medium transition-all hover:brightness-110 active:scale-[0.97]"
                style={{ background: '#D97706', color: '#14100D' }}
              >
                Save Settings
              </button>
            </div>
          </motion.div>
        );

      case 'system':
        return (
          <motion.div
            key="system"
            variants={tabContentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={tabContentTransition}
            className="max-w-[640px] space-y-5"
          >
            <SettingCard title="Ingestion Preferences">
              <div className="space-y-4">
                {/* Data directory */}
                <div>
                  <label className="flex items-center gap-1.5 text-[12px] text-[#B8A88A] mb-1.5">
                    <FolderOpen className="size-3" />
                    Data Directory
                  </label>
                  <input
                    type="text"
                    value={dataDir}
                    onChange={(e) => setDataDir(e.target.value)}
                    className="w-full h-9 px-3 text-sm rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors font-mono"
                    style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                  />
                </div>

                {/* Max file size */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[12px] text-[#B8A88A]">Max Upload Size</label>
                    <span className="text-[11px] text-[#FBBF24] font-mono">{maxFileSize} MB</span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={100}
                    value={maxFileSize}
                    onChange={(e) => setMaxFileSize(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #D97706 ${(maxFileSize - 10) / 90 * 100}%, #78350F30 ${(maxFileSize - 10) / 90 * 100}%)`,
                    }}
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-[10px] text-[#7A6B5A]">10 MB</span>
                    <span className="text-[10px] text-[#7A6B5A]">100 MB</span>
                  </div>
                </div>

                {/* Auto-ingest toggle */}
                <div className="flex items-center justify-between py-1">
                  <div>
                    <div className="text-sm text-[#EDE4D3]">Auto-ingest on upload</div>
                    <div className="text-[11px] text-[#7A6B5A]">Process files immediately on upload</div>
                  </div>
                  <Toggle checked={autoIngest} onChange={setAutoIngest} />
                </div>

                {/* Auto-analyze toggle */}
                <div className="flex items-center justify-between py-1">
                  <div>
                    <div className="text-sm text-[#EDE4D3]">Auto-analyze after ingestion</div>
                    <div className="text-[11px] text-[#7A6B5A]">Run Munger analysis after ingestion completes</div>
                  </div>
                  <Toggle checked={autoAnalyze} onChange={setAutoAnalyze} />
                </div>

                {/* Language */}
                <div>
                  <label className="flex items-center gap-1.5 text-[12px] text-[#B8A88A] mb-1.5">
                    <Languages className="size-3" />
                    Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full h-9 px-3 text-sm rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                    style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                  >
                    <option value="en">English</option>
                    <option value="zh">Chinese (中文)</option>
                  </select>
                </div>
              </div>
            </SettingCard>
          </motion.div>
        );

      case 'appearance':
        return (
          <motion.div
            key="appearance"
            variants={tabContentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={tabContentTransition}
            className="max-w-[640px] space-y-5"
          >
            {/* Theme */}
            <SettingCard title="Theme">
              <div className="grid grid-cols-3 gap-3">
                {[
                  { key: 'dark' as const, label: 'Dark', icon: <Moon className="size-5" /> },
                  { key: 'light' as const, label: 'Light', icon: <Sun className="size-5" /> },
                  { key: 'system' as const, label: 'System', icon: <Monitor className="size-5" /> },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setTheme(t.key)}
                    className={cn(
                      'flex flex-col items-center gap-2 py-4 px-3 rounded-lg border transition-all',
                      theme === t.key
                        ? 'border-[#D97706] bg-[#D9770610] shadow-[0_0_20px_rgba(251,191,36,0.06)]'
                        : 'border-[#78350F20] hover:border-[#78350F50] bg-transparent'
                    )}
                  >
                    <div className={cn('text-[#B8A88A]', theme === t.key && 'text-[#FBBF24]')}>{t.icon}</div>
                    <span className={cn('text-xs font-medium', theme === t.key ? 'text-[#EDE4D3]' : 'text-[#B8A88A]')}>
                      {t.label}
                    </span>
                    {theme === t.key && (
                      <div className="size-4 rounded-full bg-[#D97706] flex items-center justify-center">
                        <Check className="size-2.5 text-[#14100D]" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </SettingCard>

            {/* Font Size */}
            <SettingCard title="Font Size">
              <div className="flex items-center gap-1 p-1 rounded-lg bg-[#0F0C09] border" style={{ borderColor: 'rgba(120, 53, 15, 0.2)' }}>
                {[
                  { key: 'small' as const, label: 'Small' },
                  { key: 'medium' as const, label: 'Medium' },
                  { key: 'large' as const, label: 'Large' },
                ].map((fs) => (
                  <button
                    key={fs.key}
                    onClick={() => setFontSize(fs.key)}
                    className={cn(
                      'flex-1 h-8 rounded-md text-xs font-medium transition-all',
                      fontSize === fs.key
                        ? 'bg-[#2D2620] text-[#EDE4D3]'
                        : 'text-[#7A6B5A] hover:text-[#B8A88A]'
                    )}
                  >
                    {fs.label}
                  </button>
                ))}
              </div>
            </SettingCard>

            {/* Density */}
            <SettingCard title="Interface Density">
              <div className="flex items-center gap-1 p-1 rounded-lg bg-[#0F0C09] border" style={{ borderColor: 'rgba(120, 53, 15, 0.2)' }}>
                {[
                  { key: 'compact' as const, label: 'Compact' },
                  { key: 'default' as const, label: 'Default' },
                  { key: 'relaxed' as const, label: 'Relaxed' },
                ].map((d) => (
                  <button
                    key={d.key}
                    onClick={() => setDensity(d.key)}
                    className={cn(
                      'flex-1 h-8 rounded-md text-xs font-medium transition-all',
                      density === d.key
                        ? 'bg-[#2D2620] text-[#EDE4D3]'
                        : 'text-[#7A6B5A] hover:text-[#B8A88A]'
                    )}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </SettingCard>
          </motion.div>
        );

      case 'data':
        return (
          <motion.div
            key="data"
            variants={tabContentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={tabContentTransition}
            className="max-w-[640px] space-y-5"
          >
            {/* Storage Usage */}
            <SettingCard title="Storage">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[#B8A88A]">{(storageUsed / 1024).toFixed(2)} GB used</span>
                  <span className="text-[#7A6B5A]">of {(storageTotal / 1024).toFixed(2)} GB</span>
                </div>
                <div className="h-2 rounded-full bg-[#78350F30] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${storagePercent}%`,
                      background: storagePercent > 85 ? '#B91C1C' : storagePercent > 70 ? '#CA8A04' : '#D97706',
                    }}
                  />
                </div>
                <div className="text-[11px] text-[#7A6B5A]">{storagePercent}% used</div>
              </div>
            </SettingCard>

            {/* Export */}
            <SettingCard title="Export Data">
              <div className="flex flex-col gap-2">
                <button
                  className="flex items-center gap-2 h-9 px-3 rounded-md text-sm border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
                  style={{ borderColor: '#78350F40' }}
                  onClick={() => alert('Export started!')}
                >
                  <Download className="size-3.5" />
                  Export All Data
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[#251F18] text-[#7A6B5A] font-mono">ZIP</span>
                </button>
              </div>
            </SettingCard>

            {/* Import */}
            <SettingCard title="Import Data">
              <div className="flex flex-col gap-2">
                <button
                  className="flex items-center gap-2 h-9 px-3 rounded-md text-sm border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
                  style={{ borderColor: '#78350F40' }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="size-3.5" />
                  Import Data
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[#251F18] text-[#7A6B5A] font-mono">ZIP</span>
                </button>
                <input ref={fileInputRef} type="file" accept=".zip" className="hidden" onChange={() => alert('Import started!')} />
              </div>
            </SettingCard>

            {/* Danger Zone */}
            <SettingCard title="Danger Zone" className="border-[#B91C1C30]">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-[#EDE4D3]">Clear All Wiki Pages</div>
                    <div className="text-[11px] text-[#7A6B5A]">Remove all wiki pages but keep settings</div>
                  </div>
                  <button
                    onClick={() => { setConfirmText(''); setClearDialogOpen(true); }}
                    className="h-8 px-3 rounded-md text-xs font-medium bg-[#B91C1C] text-white hover:brightness-110 transition-all active:scale-[0.97]"
                  >
                    <Trash2 className="size-3 inline mr-1" />
                    Clear
                  </button>
                </div>
                <div className="h-px bg-[#78350F15]" />
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-[#EDE4D3]">Reset Database</div>
                    <div className="text-[11px] text-[#7A6B5A]">Delete all data and reset to factory defaults</div>
                  </div>
                  <button
                    onClick={() => { setConfirmText(''); setResetDialogOpen(true); }}
                    className="h-8 px-3 rounded-md text-xs font-medium bg-[#B91C1C] text-white hover:brightness-110 transition-all active:scale-[0.97]"
                  >
                    <AlertTriangle className="size-3 inline mr-1" />
                    Reset
                  </button>
                </div>
              </div>
            </SettingCard>

            {/* Clear Confirmation Dialog */}
            <AnimatePresence>
              {clearDialogOpen && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
                  onClick={() => setClearDialogOpen(false)}
                >
                  <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full max-w-sm rounded-xl border p-6"
                    style={{ background: '#1C1712', borderColor: 'rgba(120, 53, 15, 0.2)' }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="size-5 text-[#B91C1C]" />
                      <h3 className="text-lg font-semibold text-[#EDE4D3]">Clear All Wiki Pages</h3>
                    </div>
                    <p className="text-sm text-[#B8A88A] mb-4">
                      This will permanently delete all wiki pages. This action cannot be undone.
                    </p>
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setClearDialogOpen(false)}
                        className="h-8 px-3 rounded-md text-xs border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
                        style={{ borderColor: '#78350F40' }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => { setClearDialogOpen(false); alert('All wiki pages cleared!'); }}
                        className="h-8 px-3 rounded-md text-xs font-medium bg-[#B91C1C] text-white hover:brightness-110 transition-all"
                      >
                        Clear All
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Reset Confirmation Dialog */}
            <AnimatePresence>
              {resetDialogOpen && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
                  onClick={() => setResetDialogOpen(false)}
                >
                  <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full max-w-sm rounded-xl border p-6"
                    style={{ background: '#1C1712', borderColor: 'rgba(120, 53, 15, 0.2)' }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="size-5 text-[#B91C1C]" />
                      <h3 className="text-lg font-semibold text-[#EDE4D3]">Reset Database</h3>
                    </div>
                    <p className="text-sm text-[#B8A88A] mb-3">
                      Type <span className="font-mono text-[#FBBF24]">RESET</span> to confirm. This will delete ALL data permanently.
                    </p>
                    <input
                      type="text"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      placeholder="Type RESET..."
                      className="w-full h-9 px-3 text-sm rounded-md border bg-transparent text-[#EDE4D3] placeholder-[#7A6B5A] outline-none focus:border-[#D97706] transition-colors font-mono mb-4"
                      style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setResetDialogOpen(false)}
                        className="h-8 px-3 rounded-md text-xs border text-[#B8A88A] hover:text-[#EDE4D3] hover:bg-[#251F18] transition-all"
                        style={{ borderColor: '#78350F40' }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          if (confirmText === 'RESET') {
                            setResetDialogOpen(false);
                            alert('Database reset!');
                          }
                        }}
                        className={cn(
                          'h-8 px-3 rounded-md text-xs font-medium transition-all',
                          confirmText === 'RESET'
                            ? 'bg-[#B91C1C] text-white hover:brightness-110'
                            : 'bg-[#78350F30] text-[#7A6B5A] cursor-not-allowed'
                        )}
                      >
                        Reset Database
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );

      case 'advanced':
        return (
          <motion.div
            key="advanced"
            variants={tabContentVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={tabContentTransition}
            className="max-w-[640px] space-y-5"
          >
            <SettingCard title="Debugging">
              <div className="space-y-4">
                {/* Debug mode toggle */}
                <div className="flex items-center justify-between py-1">
                  <div>
                    <div className="text-sm text-[#EDE4D3]">Debug Mode</div>
                    <div className="text-[11px] text-[#7A6B5A]">Show internal IDs and raw data in the UI</div>
                  </div>
                  <Toggle checked={debugMode} onChange={setDebugMode} />
                </div>

                {/* Log level */}
                <div>
                  <label className="text-[12px] text-[#B8A88A] mb-1.5 block">Log Level</label>
                  <select
                    value={logLevel}
                    onChange={(e) => setLogLevel(e.target.value)}
                    className="w-full h-9 px-3 text-sm rounded-md border bg-transparent text-[#EDE4D3] outline-none focus:border-[#D97706] transition-colors"
                    style={{ borderColor: 'rgba(120, 53, 15, 0.25)', background: '#0F0C09' }}
                  >
                    <option value="error">Error</option>
                    <option value="warn">Warn</option>
                    <option value="info">Info</option>
                    <option value="debug">Debug</option>
                  </select>
                </div>
              </div>
            </SettingCard>

            <SettingCard title="Performance">
              <div className="space-y-4">
                {/* API timeout */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="flex items-center gap-1.5 text-[12px] text-[#B8A88A]">
                      <Clock className="size-3" />
                      API Request Timeout
                    </label>
                    <span className="text-[11px] text-[#FBBF24] font-mono">{apiTimeout}s</span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={120}
                    value={apiTimeout}
                    onChange={(e) => setApiTimeout(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #D97706 ${(apiTimeout - 10) / 110 * 100}%, #78350F30 ${(apiTimeout - 10) / 110 * 100}%)`,
                    }}
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-[10px] text-[#7A6B5A]">10s</span>
                    <span className="text-[10px] text-[#7A6B5A]">120s</span>
                  </div>
                </div>

                {/* Max concurrent jobs */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[12px] text-[#B8A88A]">Max Concurrent Jobs</label>
                    <span className="text-[11px] text-[#FBBF24] font-mono">{maxConcurrent}</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={maxConcurrent}
                    onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #D97706 ${(maxConcurrent - 1) / 9 * 100}%, #78350F30 ${(maxConcurrent - 1) / 9 * 100}%)`,
                    }}
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-[10px] text-[#7A6B5A]">1</span>
                    <span className="text-[10px] text-[#7A6B5A]">10</span>
                  </div>
                </div>
              </div>
            </SettingCard>

            {/* Reset to defaults */}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => {
                  if (confirm('Reset all settings to defaults?')) {
                    setDefaultProvider('ollama');
                    setOllamaUrl('http://localhost:11434');
                    setOllamaModel('llama3.2');
                    setOpenaiKey('');
                    setOpenaiModel('gpt-4o');
                    setAnthropicKey('');
                    setAnthropicModel('claude-3-5-sonnet-20241022');
                    setDataDir('/home/user/.munger/data');
                    setMaxFileSize(50);
                    setAutoIngest(true);
                    setAutoAnalyze(true);
                    setLanguage('en');
                    setTheme('dark');
                    setFontSize('medium');
                    setDensity('default');
                    setDebugMode(false);
                    setLogLevel('info');
                    setApiTimeout(60);
                    setMaxConcurrent(3);
                  }
                }}
                className="flex items-center gap-1.5 h-8 px-3 rounded-md text-xs text-[#7A6B5A] hover:text-[#B8A88A] hover:bg-[#251F18] transition-all"
              >
                <RotateCcw className="size-3" />
                Reset to Defaults
              </button>
            </div>
          </motion.div>
        );
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
        className="px-6 pt-8 pb-4 shrink-0"
      >
        <h1 className="font-display text-4xl font-semibold text-[#EDE4D3]">Settings</h1>
        <p className="text-[15px] text-[#B8A88A] mt-1">
          Configure Munger to work the way you think
        </p>
      </motion.div>

      {/* Tab Navigation */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="px-6 shrink-0 border-b"
        style={{ borderColor: 'rgba(120, 53, 15, 0.2)' }}
      >
        <div className="flex gap-0">
          {TABS.map((tab, i) => (
            <motion.button
              key={tab.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.3 }}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors',
                activeTab === tab.id ? 'text-[#EDE4D3]' : 'text-[#7A6B5A] hover:text-[#B8A88A]'
              )}
            >
              {tab.icon}
              {tab.label}
              {activeTab === tab.id && (
                <motion.div
                  layoutId="settings-tab-underline"
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#FBBF24]"
                  transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
                />
              )}
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <AnimatePresence mode="wait">
          {renderTabContent()}
        </AnimatePresence>
      </div>
    </div>
  );
}
