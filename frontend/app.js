// Inject premium cursor and follow-up suggestion styles dynamically
if (typeof document !== 'undefined') {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulseCursor {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }
        .streaming-cursor {
            display: inline-block;
            width: 2px;
            height: 15px;
            background-color: var(--accent);
            margin-left: 4px;
            vertical-align: middle;
            animation: pulseCursor 0.8s infinite;
        }
        .follow-up-suggestions-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
            animation: fadeIn 0.3s ease forwards;
            align-self: flex-start;
        }
        .follow-up-chip {
            background-color: var(--accent-light);
            color: var(--accent);
            border: 1px solid var(--border);
            padding: 8px 16px;
            border-radius: 20px;
            font-family: var(--font-body);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 2px 4px var(--shadow);
        }
        .follow-up-chip:hover {
            background-color: var(--accent);
            color: var(--text-on-accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(122, 162, 247, 0.25);
            border-color: transparent;
        }
    `;
    document.head.appendChild(style);
}

const { useState, useEffect, useRef } = React;
const RechartsComponents = window.Recharts || {};
const { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } = RechartsComponents;

const API_BASE = 'http://localhost:8000';

// Custom SVG Illustrations for Empty States
function EmptyIllustration() {
    return (
        <svg className="empty-state-illustration" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <path d="M12 8v4" />
            <path d="M12 16h.01" />
            <path d="M12 3a9 9 0 0 1 9 9a9 9 0 0 1 -9 9a9 9 0 0 1 -9 -9a9 9 0 0 1 9 -9z" />
        </svg>
    );
}

// Shimmer Skeleton Screen Component
function SkeletonLoader() {
    return (
        <div className="skeleton-msg-wrapper">
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '8px' }}>
                <div className="skeleton-item skeleton-avatar"></div>
                <div className="skeleton-item skeleton-line short" style={{ height: '12px' }}></div>
            </div>
            <div className="skeleton-item skeleton-line"></div>
            <div className="skeleton-item skeleton-line mid"></div>
            <div className="skeleton-item skeleton-line short"></div>
            <div className="skeleton-item skeleton-chart-box"></div>
        </div>
    );
}

// Login Screen Component
function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const res = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Invalid credentials');
            }
            const data = await res.json();
            onLogin(data);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="login-wrapper">
            <div className="login-card">
                <div className="login-logo">Amrita Guard</div>
                <div className="login-subtext">Enterprise Revenue Leakage & Audit Center</div>
                
                {error && <div className="login-error">{error}</div>}
                
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column' }}>
                    <input 
                        className="login-input" 
                        type="text" 
                        placeholder="Username" 
                        value={username} 
                        onChange={e => setUsername(e.target.value)} 
                        required 
                    />
                    <input 
                        className="login-input" 
                        type="password" 
                        placeholder="Password" 
                        value={password} 
                        onChange={e => setPassword(e.target.value)} 
                        required 
                    />
                    <button type="submit" className="login-btn">
                        Authenticate
                    </button>
                </form>
                
                <div style={{ marginTop: '24px', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    <strong>Access Hints:</strong><br/>
                    Admin / Admin (Revenue & Audit)<br/>
                    Admin1 / Admin1 (Revenue Only)<br/>
                    Admin2 / Admin2 (Audit Only)
                </div>
            </div>
        </div>
    );
}

// CommandPalette Component (Linear/Superhuman Style)
function CommandPalette({ 
    isOpen, 
    onClose, 
    bot, 
    setBot, 
    user, 
    filters, 
    setFilters, 
    handleSend, 
    loadSession, 
    theme, 
    toggleTheme, 
    handleNewChat, 
    onLogout, 
    messages 
}) {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState({ departments: [], surgeons: [], sessions: [] });
    const [results, setResults] = useState([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const fuseRef = useRef(null);

    // Fetch dynamic options from backend suggestions endpoint
    useEffect(() => {
        if (!isOpen) return;
        
        fetch(`${API_BASE}/api/search-suggestions?username=${encodeURIComponent(user?.username || '')}`)
            .then(res => res.json())
            .then(data => {
                setSuggestions(data);
                
                const searchItems = [];
                
                // 1. Static Commands
                searchItems.push(
                    { type: 'command', name: 'Switch to Revenue bot', actionType: 'switch-bot', value: 'revenue', icon: '💰' },
                    { type: 'command', name: 'Switch to Audit bot', actionType: 'switch-bot', value: 'audit', icon: '🏥' },
                    { type: 'command', name: 'Clear filters', actionType: 'clear-filters', icon: '🧹' },
                    { type: 'command', name: 'Export last response as PDF', actionType: 'export-pdf', icon: '📄' },
                    { type: 'command', name: 'Toggle Color Theme', actionType: 'toggle-theme', icon: '🌓' },
                    { type: 'command', name: 'Start a New Chat Session', actionType: 'new-chat', icon: '💬' },
                    { type: 'command', name: 'Sign Out of Portal', actionType: 'logout', icon: '🚪' }
                );

                // 2. Date ranges
                searchItems.push(
                    { type: 'date', name: 'Filter by date: last month', value: 'last month', icon: '📅' },
                    { type: 'date', name: 'Filter by date: Q3', value: 'Q3', icon: '📅' }
                );

                // 3. Departments
                if (data.departments) {
                    data.departments.forEach(dept => {
                        searchItems.push({
                            type: 'department',
                            name: `Filter by department: ${dept}`,
                            value: dept,
                            icon: '🏢'
                        });
                    });
                }

                // 4. Surgeons
                if (data.surgeons) {
                    data.surgeons.forEach(surgeon => {
                        searchItems.push({
                            type: 'surgeon',
                            name: `Show leakage for ${surgeon}`,
                            value: surgeon,
                            icon: '🧑‍⚕️'
                        });
                    });
                }

                // 5. Chat Sessions
                if (data.sessions) {
                    data.sessions.forEach(session => {
                        searchItems.push({
                            type: 'session',
                            name: `Switch to chat: ${session.title}`,
                            value: session.session_id,
                            bot: session.bot,
                            icon: '💬'
                        });
                    });
                }

                // Initialize Fuse
                const fuseOptions = {
                    keys: ['name', 'value'],
                    threshold: 0.35,
                    distance: 100
                };
                
                fuseRef.current = new window.Fuse(searchItems, fuseOptions);
                setResults(searchItems);
            })
            .catch(err => {
                console.error("Error fetching suggestions:", err);
            });
    }, [isOpen, user]);

    // Handle query filtering
    useEffect(() => {
        if (!fuseRef.current) return;
        
        if (!query.trim()) {
            setResults(fuseRef.current._docs);
            setSelectedIndex(0);
            return;
        }

        const fuseResults = fuseRef.current.search(query);
        setResults(fuseResults.map(r => r.item));
        setSelectedIndex(0);
    }, [query]);

    // Keyboard navigation
    const handleKeyDown = (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex(prev => (results.length > 0 ? (prev + 1) % results.length : 0));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex(prev => (results.length > 0 ? (prev - 1 + results.length) % results.length : 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (results[selectedIndex]) {
                handleItemSelect(results[selectedIndex]);
            }
        }
    };

    // Export last response as PDF
    const exportLastResponseAsPdf = () => {
        const botMessages = messages[bot]?.filter(m => m.role === 'bot') || [];
        if (botMessages.length === 0) {
            alert("No response found in active chat to export as PDF.");
            return;
        }
        const lastMsg = botMessages[botMessages.length - 1];
        
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        doc.setFont("Helvetica", "bold");
        doc.setFontSize(16);
        doc.text(`Amrita Guard Audit Summary`, 14, 20);
        
        doc.setFontSize(11);
        doc.setFont("Helvetica", "normal");
        doc.text(`Bot Type: ${bot === 'revenue' ? 'Revenue Leakage Bot' : 'Surgery Audit Bot'}`, 14, 26);
        doc.text(`Exported: ${new Date().toLocaleString()}`, 14, 31);
        doc.line(14, 34, 196, 34);
        
        const splitText = doc.splitTextToSize(lastMsg.text, 182);
        doc.text(splitText, 14, 42);
        
        // Log PDF export event
        fetch(`${API_BASE}/export/pdf?username=${encodeURIComponent(user.username)}`, { method: 'POST' }).catch(console.error);
        
        doc.save(`Amrita_Guard_Export_${Date.now()}.pdf`);
    };

    // Dynamic date calculations
    const getDateRange = (rangeType) => {
        const now = new Date(2026, 4, 26); // May 26, 2026
        const currentYear = now.getFullYear();
        if (rangeType === 'last month') {
            const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const lastDayOfPrevMonth = new Date(now.getFullYear(), now.getMonth(), 0);
            
            const pad = (n) => String(n).padStart(2, '0');
            const start = `${prevMonth.getFullYear()}-${pad(prevMonth.getMonth() + 1)}-01`;
            const end = `${lastDayOfPrevMonth.getFullYear()}-${pad(lastDayOfPrevMonth.getMonth() + 1)}-${pad(lastDayOfPrevMonth.getDate())}`;
            return { start, end };
        } else if (rangeType === 'Q3') {
            return { start: `${currentYear}-07-01`, end: `${currentYear}-09-30` };
        }
        return { start: '', end: '' };
    };

    // Action Execution
    const handleItemSelect = (item) => {
        onClose();
        
        if (item.type === 'command') {
            switch (item.actionType) {
                case 'switch-bot':
                    setBot(item.value);
                    break;
                case 'clear-filters':
                    setFilters({ period: 'all', start: '', end: '', location: '' });
                    break;
                case 'export-pdf':
                    exportLastResponseAsPdf();
                    break;
                case 'toggle-theme':
                    toggleTheme();
                    break;
                case 'new-chat':
                    handleNewChat();
                    break;
                case 'logout':
                    onLogout();
                    break;
                default:
                    break;
            }
        } else if (item.type === 'date') {
            const { start, end } = getDateRange(item.value);
            setFilters({
                ...filters,
                period: 'custom',
                start,
                end
            });
        } else if (item.type === 'department') {
            setFilters({
                ...filters,
                location: item.value
            });
        } else if (item.type === 'surgeon') {
            setBot('audit');
            handleSend(`Show leakage for ${item.value}`, null, 'audit');
        } else if (item.type === 'session') {
            setBot(item.bot);
            loadSession(item.value);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="command-palette" onClick={e => e.stopPropagation()}>
                <div className="palette-search-wrapper">
                    <span style={{ fontSize: '18px', color: 'rgba(255, 255, 255, 0.4)', display: 'flex', alignItems: 'center' }}>🔍</span>
                    <input 
                        type="text"
                        className="palette-search-input"
                        placeholder="Search commands, departments, surgeons, sessions..."
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        autoFocus
                    />
                    <span className="palette-close-hint">esc</span>
                </div>
                <div className="palette-list">
                    {results.map((item, idx) => (
                        <button 
                            key={idx}
                            className={`palette-item ${idx === selectedIndex ? 'selected' : ''}`}
                            onClick={() => handleItemSelect(item)}
                            onMouseEnter={() => setSelectedIndex(idx)}
                        >
                            <div className="palette-item-left">
                                <span className="palette-item-icon">{item.icon}</span>
                                <span>{item.name}</span>
                            </div>
                            <span className="palette-item-shortcut">⏎</span>
                        </button>
                    ))}
                    {results.length === 0 && (
                        <div style={{ padding: '24px 16px', fontStyle: 'italic', fontSize: '13px', color: 'rgba(255, 255, 255, 0.4)', textAlign: 'center' }}>
                            No matches found for "{query}"
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// AuditLogsView Component (Admin Only compliance page)
function AuditLogsView({ user, API_BASE }) {
    const [activeTab, setActiveTab] = useState('system_logs'); // 'system_logs' | 'feedback_logs'
    const [logs, setLogs] = useState([]);
    const [feedbacks, setFeedbacks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [feedbackLoading, setFeedbackLoading] = useState(false);
    const [search, setSearch] = useState('');
    const [userFilter, setUserFilter] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [selectedLog, setSelectedLog] = useState(null); // for inspect modal
    const [selectedFeedback, setSelectedFeedback] = useState(null); // for inspect modal

    const fetchLogs = async () => {
        setLoading(true);
        try {
            let url = `${API_BASE}/audit-logs?username=${encodeURIComponent(user.username)}`;
            if (search) url += `&search=${encodeURIComponent(search)}`;
            if (userFilter) url += `&user_filter=${encodeURIComponent(userFilter)}`;
            if (actionFilter) url += `&action_filter=${encodeURIComponent(actionFilter)}`;
            if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
            if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Failed to fetch logs");
            const data = await res.json();
            setLogs(data.logs || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchFeedback = async () => {
        setFeedbackLoading(true);
        try {
            const res = await fetch(`${API_BASE}/feedback/export?username=${encodeURIComponent(user.username)}`);
            if (!res.ok) throw new Error("Failed to fetch feedback");
            const data = await res.json();
            setFeedbacks(data.feedback || []);
        } catch (err) {
            console.error(err);
        } finally {
            setFeedbackLoading(false);
        }
    };

    useEffect(() => {
        if (activeTab === 'system_logs') {
            fetchLogs();
        } else {
            fetchFeedback();
        }
    }, [activeTab, search, userFilter, actionFilter, startDate, endDate]);

    const handleDownloadCsv = () => {
        let url = `${API_BASE}/audit-logs/export?username=${encodeURIComponent(user.username)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (userFilter) url += `&user_filter=${encodeURIComponent(userFilter)}`;
        if (actionFilter) url += `&action_filter=${encodeURIComponent(actionFilter)}`;
        if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
        if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
        
        window.open(url, '_blank');
    };

    const handleDownloadFeedbackCsv = () => {
        const url = `${API_BASE}/feedback/export/csv?username=${encodeURIComponent(user.username)}`;
        window.open(url, '_blank');
    };

    const getActionBadgeClass = (action) => {
        switch (action) {
            case 'LOGIN': return 'badge-login';
            case 'LOGIN_FAILED': return 'badge-login-failed';
            case 'LOGOUT': return 'badge-logout';
            case 'QUERY_SUBMITTED': return 'badge-query';
            case 'EXPORT_PDF': return 'badge-pdf';
            case 'EXPORT_EXCEL': return 'badge-excel';
            case 'FILE_UPLOAD': return 'badge-upload';
            case 'FILTER_CHANGED': return 'badge-filter';
            case 'CHART_DRILLDOWN': return 'badge-drilldown';
            default: return 'badge-default';
        }
    };

    return (
        <div className="audit-logs-view">
            <div className="audit-header">
                <div>
                    <h3 className="audit-view-title">Compliance Audit Registry</h3>
                    <p className="audit-view-subtitle">Real-time system transaction tracking and training feedback logs</p>
                </div>
                {activeTab === 'system_logs' ? (
                    <button className="audit-download-btn" onClick={handleDownloadCsv}>
                        📥 Export Audit CSV
                    </button>
                ) : (
                    <button className="audit-download-btn" onClick={handleDownloadFeedbackCsv} style={{ backgroundColor: 'var(--success)', border: 'none', color: 'white' }}>
                        📥 Export Feedback CSV
                    </button>
                )}
            </div>

            {/* Sub-tab Navigation */}
            <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border)' }}>
                <button 
                    onClick={() => setActiveTab('system_logs')}
                    style={{
                        padding: '10px 4px',
                        fontWeight: '600',
                        fontSize: '13px',
                        background: 'none',
                        border: 'none',
                        borderBottom: activeTab === 'system_logs' ? '2px solid var(--accent)' : '2px solid transparent',
                        color: activeTab === 'system_logs' ? 'var(--accent)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    📋 System Access Logs
                </button>
                <button 
                    onClick={() => setActiveTab('feedback_logs')}
                    style={{
                        padding: '10px 4px',
                        fontWeight: '600',
                        fontSize: '13px',
                        background: 'none',
                        border: 'none',
                        borderBottom: activeTab === 'feedback_logs' ? '2px solid var(--accent)' : '2px solid transparent',
                        color: activeTab === 'feedback_logs' ? 'var(--accent)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    👍 Human Training Feedback
                </button>
            </div>

            {activeTab === 'system_logs' ? (
                <>
                    {/* Filters Row */}
                    <div className="audit-filters-grid">
                        <input 
                            type="text" 
                            placeholder="Search logs..." 
                            className="audit-filter-input"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                        <select 
                            className="audit-filter-select"
                            value={userFilter}
                            onChange={e => setUserFilter(e.target.value)}
                        >
                            <option value="">All Users</option>
                            <option value="Admin">Admin</option>
                            <option value="Admin1">Admin1</option>
                            <option value="Admin2">Admin2</option>
                        </select>
                        <select 
                            className="audit-filter-select"
                            value={actionFilter}
                            onChange={e => setActionFilter(e.target.value)}
                        >
                            <option value="">All Actions</option>
                            <option value="LOGIN">LOGIN</option>
                            <option value="LOGIN_FAILED">LOGIN_FAILED</option>
                            <option value="LOGOUT">LOGOUT</option>
                            <option value="QUERY_SUBMITTED">QUERY_SUBMITTED</option>
                            <option value="EXPORT_PDF">EXPORT_PDF</option>
                            <option value="EXPORT_EXCEL">EXPORT_EXCEL</option>
                            <option value="FILE_UPLOAD">FILE_UPLOAD</option>
                            <option value="FILTER_CHANGED">FILTER_CHANGED</option>
                            <option value="CHART_DRILLDOWN">CHART_DRILLDOWN</option>
                        </select>
                        <input 
                            type="date" 
                            className="audit-filter-input"
                            value={startDate}
                            onChange={e => setStartDate(e.target.value)}
                        />
                        <input 
                            type="date" 
                            className="audit-filter-input"
                            value={endDate}
                            onChange={e => setEndDate(e.target.value)}
                        />
                    </div>

                    {/* Table */}
                    <div className="audit-table-wrapper">
                        {loading ? (
                            <div className="audit-loading">
                                <div className="w-8 h-8 rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] animate-spin"></div>
                                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>Fetching audit records...</span>
                            </div>
                        ) : logs.length === 0 ? (
                            <div className="audit-empty">No matching compliance logs found.</div>
                        ) : (
                            <table className="audit-table">
                                <thead>
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>User</th>
                                        <th>Action</th>
                                        <th>IP Address</th>
                                        <th>Session ID</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {logs.map((log) => (
                                        <tr key={log.id} onClick={() => setSelectedLog(log)} style={{ cursor: 'pointer' }}>
                                            <td className="audit-td-time">{log.timestamp}</td>
                                            <td className="audit-td-user">{log.user_id}</td>
                                            <td>
                                                <span className={`audit-badge ${getActionBadgeClass(log.action_type)}`}>
                                                    {log.action_type}
                                                </span>
                                            </td>
                                            <td className="audit-td-ip">{log.ip_address || 'N/A'}</td>
                                            <td className="audit-td-session">{log.session_id ? log.session_id.substring(0, 8) + '...' : 'N/A'}</td>
                                            <td>
                                                <button className="audit-inspect-btn" onClick={(e) => { e.stopPropagation(); setSelectedLog(log); }}>
                                                    Inspect
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </>
            ) : (
                /* Human Feedback Table */
                <div className="audit-table-wrapper">
                    {feedbackLoading ? (
                        <div className="audit-loading">
                            <div className="w-8 h-8 rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] animate-spin"></div>
                            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>Fetching human training ratings...</span>
                        </div>
                    ) : feedbacks.length === 0 ? (
                        <div className="audit-empty">No training feedback entries recorded yet.</div>
                    ) : (
                        <table className="audit-table">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>User</th>
                                    <th>Rating / Issue</th>
                                    <th>Target Query</th>
                                    <th>Critique Comment</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                {feedbacks.map((f) => (
                                    <tr key={f.id} onClick={() => setSelectedFeedback(f)} style={{ cursor: 'pointer' }}>
                                        <td className="audit-td-time">{f.timestamp}</td>
                                        <td className="audit-td-user">{f.user_id || 'Unknown'}</td>
                                        <td>
                                            <span style={{
                                                fontSize: '11px',
                                                fontWeight: 'bold',
                                                padding: '2px 8px',
                                                borderRadius: '12px',
                                                backgroundColor: f.feedback_type === 'thumbs_up' ? 'rgba(158, 206, 106, 0.15)' : 'rgba(247, 118, 142, 0.15)',
                                                color: f.feedback_type === 'thumbs_up' ? 'var(--success)' : 'var(--danger)',
                                                textTransform: 'uppercase'
                                            }}>
                                                {f.feedback_type === 'thumbs_up' ? '👍 Helpful' : `👎 ${f.feedback_type}`}
                                            </span>
                                        </td>
                                        <td style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={f.query}>
                                            {f.query}
                                        </td>
                                        <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontStyle: f.comment ? 'normal' : 'italic', color: f.comment ? 'inherit' : 'var(--text-muted)' }}>
                                            {f.comment || 'No explanation comments provided'}
                                        </td>
                                        <td>
                                            <button className="audit-inspect-btn" onClick={(e) => { e.stopPropagation(); setSelectedFeedback(f); }}>
                                                Inspect
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Inspect Compliance Event Modal */}
            {selectedLog && (
                <div className="modal-overlay" onClick={() => setSelectedLog(null)}>
                    <div className="audit-modal-card" onClick={e => e.stopPropagation()}>
                        <div className="audit-modal-header">
                            <div>
                                <h4 className="audit-modal-title">Inspect Compliance Event</h4>
                                <p className="audit-modal-subtitle">Log ID: {selectedLog.id} &bull; {selectedLog.timestamp}</p>
                            </div>
                            <button className="audit-modal-close" onClick={() => setSelectedLog(null)}>
                                &times;
                            </button>
                        </div>
                        <div className="audit-modal-body">
                            <div className="audit-detail-row">
                                <strong>User ID:</strong> <span>{selectedLog.user_id}</span>
                            </div>
                            <div className="audit-detail-row">
                                <strong>Action Type:</strong> <span className={`audit-badge ${getActionBadgeClass(selectedLog.action_type)}`}>{selectedLog.action_type}</span>
                            </div>
                            <div className="audit-detail-row">
                                <strong>IP Address:</strong> <span>{selectedLog.ip_address || 'N/A'}</span>
                            </div>
                            <div className="audit-detail-row">
                                <strong>Session ID:</strong> <span>{selectedLog.session_id || 'N/A'}</span>
                            </div>
                            <div className="audit-detail-json-header">Raw Log Details (JSON)</div>
                            <pre className="audit-detail-json">
                                {JSON.stringify(JSON.parse(selectedLog.details), null, 2)}
                            </pre>
                        </div>
                    </div>
                </div>
            )}

            {/* Inspect Human Feedback Modal */}
            {selectedFeedback && (
                <div className="modal-overlay" onClick={() => setSelectedFeedback(null)}>
                    <div className="audit-modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                        <div className="audit-modal-header">
                            <div>
                                <h4 className="audit-modal-title">Inspect Training Feedback</h4>
                                <p className="audit-modal-subtitle">Feedback ID: {selectedFeedback.id} &bull; {selectedFeedback.timestamp}</p>
                            </div>
                            <button className="audit-modal-close" onClick={() => setSelectedFeedback(null)}>
                                &times;
                            </button>
                        </div>
                        <div className="audit-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div className="audit-detail-row">
                                <strong>User Rater:</strong> <span>{selectedFeedback.user_id || 'Unknown'}</span>
                            </div>
                            <div className="audit-detail-row">
                                <strong>Session ID:</strong> <span>{selectedFeedback.session_id || 'N/A'}</span>
                            </div>
                            <div className="audit-detail-row">
                                <strong>Rating Classification:</strong> 
                                <span style={{
                                    fontSize: '11px',
                                    fontWeight: 'bold',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    backgroundColor: selectedFeedback.feedback_type === 'thumbs_up' ? 'rgba(158, 206, 106, 0.15)' : 'rgba(247, 118, 142, 0.15)',
                                    color: selectedFeedback.feedback_type === 'thumbs_up' ? 'var(--success)' : 'var(--danger)',
                                    textTransform: 'uppercase'
                                }}>
                                    {selectedFeedback.feedback_type === 'thumbs_up' ? '👍 Helpful' : `👎 ${selectedFeedback.feedback_type}`}
                                </span>
                            </div>
                            
                            <div style={{ marginTop: '8px' }}>
                                <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>User Query Submitted:</strong>
                                <div style={{ padding: '10px', backgroundColor: 'var(--background)', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px' }}>
                                    {selectedFeedback.query}
                                </div>
                            </div>
                            
                            <div style={{ marginTop: '8px' }}>
                                <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Critic Explanation Comment:</strong>
                                <div style={{ padding: '10px', backgroundColor: 'var(--background)', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px', fontStyle: selectedFeedback.comment ? 'normal' : 'italic' }}>
                                    {selectedFeedback.comment || 'No explanation comment provided by rater.'}
                                </div>
                            </div>

                            <div style={{ marginTop: '8px' }}>
                                <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>AI Bot Response Returned:</strong>
                                <div style={{ 
                                    padding: '12px', 
                                    backgroundColor: 'var(--background)', 
                                    borderRadius: '8px', 
                                    border: '1px solid var(--border)', 
                                    fontSize: '12px', 
                                    maxHeight: '200px', 
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    fontFamily: 'monospace'
                                }}>
                                    {selectedFeedback.bot_response}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// AlertsView Management Component
function AlertsView({
    user,
    API_BASE,
    locations,
    alerts,
    fetchAlerts,
    alertModalOpen,
    setAlertModalOpen,
    currentAlert,
    setCurrentAlert,
    alertForm,
    setAlertForm,
    dryRunResults,
    setDryRunResults,
    dryRunLoading,
    setDryRunLoading,
    handleToggleAlertActive,
    handleDeleteAlert,
    handleSaveAlert,
    handleDryRunAlert,
    handleRunAlertsCheckNow
}) {
    const handleEditAlert = (alert) => {
        setCurrentAlert(alert);
        setAlertForm({
            name: alert.name,
            condition_type: alert.condition_type,
            threshold: alert.threshold.toString(),
            comparison_column: alert.comparison_column || "",
            bot_type: alert.bot_type,
            email_recipient: alert.email_recipient || "",
            webhook_url: alert.webhook_url || ""
        });
        setDryRunResults(null);
        setAlertModalOpen(true);
    };

    const getConditionDescription = (type, col) => {
        switch (type) {
            case 'total_leakage_daily':
                return "Daily Total Revenue Leakage exceeds threshold";
            case 'unbilled_rate':
                return "Daily Unbilled Procedure Rate exceeds threshold";
            case 'department_leakage':
                return `Daily leakage in department '${col}' exceeds threshold`;
            case 'surgery_loss':
                return "Daily Surgery package Audit Loss exceeds threshold";
            default:
                return type;
        }
    };

    return (
        <div className="alerts-view">
            <div className="flex justify-between items-center bg-[var(--card-background)] border border-[var(--border)] rounded-2xl p-6 shadow-lg">
                <div>
                    <h3 className="text-2xl font-bold font-heading text-[var(--text-primary)]">Alerting & Incident Monitors</h3>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">Configure automated checks and webhook/email notifications on clinical billing metrics</p>
                </div>
                <div className="flex gap-4">
                    <button 
                        className="py-2.5 px-5 bg-[var(--background)] border border-[var(--border)] hover:border-[var(--accent)] text-[var(--text-primary)] hover:text-[var(--accent)] font-semibold text-sm rounded-xl cursor-pointer transition-all flex items-center gap-2"
                        onClick={handleRunAlertsCheckNow}
                    >
                        🔄 Run Checks Now
                    </button>
                    <button 
                        className="py-2.5 px-5 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-bold text-sm rounded-xl cursor-pointer transition-all shadow-md flex items-center gap-2"
                        onClick={() => {
                            setCurrentAlert(null);
                            setAlertForm({
                                name: "",
                                condition_type: "total_leakage_daily",
                                threshold: "",
                                comparison_column: "",
                                bot_type: "revenue",
                                email_recipient: "",
                                webhook_url: ""
                            });
                            setDryRunResults(null);
                            setAlertModalOpen(true);
                        }}
                    >
                        ➕ Create Alert
                    </button>
                </div>
            </div>

            <div className="alerts-grid">
                {alerts.map(alert => (
                    <div key={alert.id} className="alert-card">
                        <div className="alert-card-header">
                            <div className="alert-card-title">{alert.name}</div>
                            <label className="switch">
                                <input 
                                    type="checkbox" 
                                    checked={alert.is_active === 1}
                                    onChange={(e) => handleToggleAlertActive(alert.id, e.target.checked)}
                                />
                                <span className="slider"></span>
                            </label>
                        </div>
                        <div className="alert-card-body">
                            <span className="alert-card-condition">
                                {getConditionDescription(alert.condition_type, alert.comparison_column)}
                            </span>
                            <div className="flex items-baseline gap-1 mt-1">
                                <span className="alert-card-threshold">
                                    {alert.condition_type === 'unbilled_rate' ? '' : '₹'}{alert.threshold.toLocaleString('en-IN')}{alert.condition_type === 'unbilled_rate' ? '%' : ''}
                                </span>
                                <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">threshold</span>
                            </div>
                        </div>
                        <div className="alert-card-footer">
                            <span className="text-[10.5px] text-[var(--text-muted)]">
                                Created by: <strong className="text-[var(--text-secondary)]">{alert.created_by}</strong>
                            </span>
                            <div className="alert-card-actions">
                                <button className="alert-card-btn" onClick={() => handleEditAlert(alert)}>Edit</button>
                                <button className="alert-card-btn delete" onClick={() => handleDeleteAlert(alert.id)}>Delete</button>
                            </div>
                        </div>
                    </div>
                ))}
                {alerts.length === 0 && (
                    <div className="col-span-full bg-[var(--card-background)] border border-[var(--border)] rounded-2xl p-12 text-center text-sm italic text-[var(--text-muted)]">
                        No metric monitors configured. Click "Create Alert" to build one!
                    </div>
                )}
            </div>

            {/* CREATE / EDIT ALERT MODAL */}
            {alertModalOpen && (
                <div className="modal-overlay" onClick={() => setAlertModalOpen(false)}>
                    <div className="alert-modal-card" onClick={e => e.stopPropagation()}>
                        <div className="p-6 border-b border-[var(--border)] flex justify-between items-center bg-[var(--card-background)]">
                            <div>
                                <h4 className="text-lg font-bold font-heading text-[var(--text-primary)]">
                                    {currentAlert ? "Modify Metric Monitor" : "Configure Incident Monitor"}
                                </h4>
                                <p className="text-xs text-[var(--text-secondary)] mt-0.5">Build conditional triggers based on historical patterns</p>
                            </div>
                            <button className="text-xl text-[var(--text-secondary)] hover:text-[var(--danger)] cursor-pointer" onClick={() => setAlertModalOpen(false)}>
                                &times;
                            </button>
                        </div>
                        <form onSubmit={handleSaveAlert} className="p-6 flex flex-col gap-6 bg-[var(--card-background)]">
                            <div className="alert-form-grid">
                                <div className="alert-form-group full-width">
                                    <label className="alert-form-label">Alert Monitor Name</label>
                                    <input 
                                        type="text" 
                                        className="alert-form-input" 
                                        placeholder="E.g., High ICU daily leakage warning" 
                                        value={alertForm.name} 
                                        onChange={e => setAlertForm({ ...alertForm, name: e.target.value })}
                                        required 
                                    />
                                </div>
                                <div className="alert-form-group">
                                    <label className="alert-form-label">Monitor System Bot</label>
                                    <select 
                                        className="alert-form-select" 
                                        value={alertForm.bot_type} 
                                        onChange={e => setAlertForm({ ...alertForm, bot_type: e.target.value })}
                                    >
                                        <option value="revenue">💰 Revenue Leakage Bot</option>
                                        <option value="audit">🏥 Surgery Audit Bot</option>
                                    </select>
                                </div>
                                <div className="alert-form-group">
                                    <label className="alert-form-label">Trigger Condition</label>
                                    <select 
                                        className="alert-form-select" 
                                        value={alertForm.condition_type} 
                                        onChange={e => setAlertForm({ ...alertForm, condition_type: e.target.value })}
                                    >
                                        <option value="total_leakage_daily">Daily Total Leakage (₹)</option>
                                        <option value="unbilled_rate">Daily Unbilled Procedure Rate (%)</option>
                                        <option value="department_leakage">Department / Specialty daily leakage (₹)</option>
                                        <option value="surgery_loss">Daily Surgery package Audit Loss (₹)</option>
                                    </select>
                                </div>

                                {alertForm.condition_type === 'department_leakage' && (
                                    <div className="alert-form-group full-width">
                                        <label className="alert-form-label">Target Department</label>
                                        <select 
                                            className="alert-form-select" 
                                            value={alertForm.comparison_column} 
                                            onChange={e => setAlertForm({ ...alertForm, comparison_column: e.target.value })}
                                            required
                                        >
                                            <option value="">-- Choose department --</option>
                                            {locations.map((loc, idx) => (
                                                <option key={idx} value={loc}>{loc}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                <div className="alert-form-group full-width">
                                    <label className="alert-form-label">Threshold Limit ({alertForm.condition_type === 'unbilled_rate' ? '%' : '₹'})</label>
                                    <input 
                                        type="number" 
                                        className="alert-form-input" 
                                        placeholder={alertForm.condition_type === 'unbilled_rate' ? "E.g., 15" : "E.g., 200000"} 
                                        value={alertForm.threshold} 
                                        onChange={e => setAlertForm({ ...alertForm, threshold: e.target.value })}
                                        required 
                                    />
                                </div>
                                <div className="alert-form-group">
                                    <label className="alert-form-label">Alert Email Recipient</label>
                                    <input 
                                        type="email" 
                                        className="alert-form-input" 
                                        placeholder="E.g., auditor@hospital.com" 
                                        value={alertForm.email_recipient} 
                                        onChange={e => setAlertForm({ ...alertForm, email_recipient: e.target.value })}
                                    />
                                </div>
                                <div className="alert-form-group">
                                    <label className="alert-form-label">Slack/Teams Webhook URL</label>
                                    <input 
                                        type="url" 
                                        className="alert-form-input" 
                                        placeholder="E.g., https://hooks.slack.com/..." 
                                        value={alertForm.webhook_url} 
                                        onChange={e => setAlertForm({ ...alertForm, webhook_url: e.target.value })}
                                    />
                                </div>
                            </div>

                            {/* DRY RUN SUBSECTION */}
                            <div className="border-t border-[var(--border)] pt-4 flex flex-col gap-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Simulation Dry-Run</span>
                                    <button 
                                        type="button"
                                        className="py-1 px-3 bg-[var(--background)] border border-[var(--border)] hover:border-[var(--accent)] text-xs font-semibold rounded-lg cursor-pointer hover:text-[var(--accent)] transition-all"
                                        onClick={handleDryRunAlert}
                                        disabled={!alertForm.threshold}
                                    >
                                        {dryRunLoading ? "Testing..." : "🔬 Simulating historical triggers"}
                                    </button>
                                </div>
                                
                                {dryRunResults && (
                                    <div className="dry-run-panel scrollbar">
                                        <div className="dry-run-header">
                                            <span>Simulated Trigger Date</span>
                                            <span>Detected Metric Value</span>
                                        </div>
                                        {dryRunResults.length === 0 ? (
                                            <div className="text-center text-[11px] text-[var(--text-muted)] italic py-2">
                                                No historical incidents would have triggered this threshold!
                                            </div>
                                        ) : (
                                            dryRunResults.map((trig, idx) => (
                                                <div key={idx} className="dry-run-row">
                                                    <span>{trig.date}</span>
                                                    <span className="triggered">
                                                        {alertForm.condition_type === 'unbilled_rate' ? '' : '₹'}{trig.value.toLocaleString('en-IN')}{alertForm.condition_type === 'unbilled_rate' ? '%' : ''}
                                                    </span>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="flex justify-end gap-3 border-t border-[var(--border)] pt-4">
                                <button type="button" className="py-2 px-4 bg-[var(--background)] border border-[var(--border)] hover:border-[var(--danger)] text-sm rounded-xl cursor-pointer hover:text-[var(--danger)] transition-all" onClick={() => setAlertModalOpen(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="py-2 px-6 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-bold rounded-xl cursor-pointer transition-all shadow-md">
                                    Save Monitor
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

// Main App Dashboard Component
function App() {
    // Identity & Settings States
    const [user, setUser] = useState(null);
    const [theme, setTheme] = useState(() => localStorage.getItem('amrita-theme') || 'dark');
    const [bot, setBot] = useState('revenue');
    const [kpis, setKpis] = useState({
        total_leakage: 0,
        unbilled_rate: 0.0,
        top_offending_dept: 'Loading...',
        top_offending_dept_amount: 0,
        surgery_audit_loss: 0,
        monthly_trend: []
    });
    
    // UI Panels & Modals
    const [commandBarOpen, setCommandBarOpen] = useState(false);
    
    // Alerts and Notifications state
    const [alerts, setAlerts] = useState([]);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [notificationPanelOpen, setNotificationPanelOpen] = useState(false);
    const [alertModalOpen, setAlertModalOpen] = useState(false);
    const [currentAlert, setCurrentAlert] = useState(null);
    const [alertForm, setAlertForm] = useState({
        name: "",
        condition_type: "total_leakage_daily",
        threshold: "",
        comparison_column: "",
        bot_type: "revenue",
        email_recipient: "",
        webhook_url: ""
    });
    const [dryRunResults, setDryRunResults] = useState(null);
    const [dryRunLoading, setDryRunLoading] = useState(false);

    const fetchAlerts = async () => {
        if (!user) return;
        try {
            const res = await fetch(`${API_BASE}/api/alerts?username=${user.username}`);
            const data = await res.json();
            setAlerts(data.alerts || []);
        } catch (e) {
            console.error("Failed to fetch alerts:", e);
        }
    };

    const fetchNotifications = async () => {
        if (!user) return;
        try {
            const res = await fetch(`${API_BASE}/api/alerts/notifications?username=${user.username}`);
            const data = await res.json();
            setNotifications(data.notifications || []);
        } catch (e) {
            console.error("Failed to fetch notifications:", e);
        }
    };

    const fetchUnreadCount = async () => {
        if (!user) return;
        try {
            const res = await fetch(`${API_BASE}/api/alerts/notifications/unread-count?username=${user.username}`);
            const data = await res.json();
            setUnreadCount(data.unread_count || 0);
        } catch (e) {
            console.error("Failed to fetch unread count:", e);
        }
    };

    const handleToggleAlertActive = async (alertId, isActive) => {
        try {
            const res = await fetch(`${API_BASE}/api/alerts/${alertId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: isActive ? 1 : 0 })
            });
            if (res.ok) fetchAlerts();
        } catch (e) {
            console.error(e);
        }
    };

    const handleDeleteAlert = async (alertId) => {
        if (!confirm("Are you sure you want to delete this alert?")) return;
        try {
            const res = await fetch(`${API_BASE}/api/alerts/${alertId}?username=${user.username}`, {
                method: 'DELETE'
            });
            if (res.ok) fetchAlerts();
        } catch (e) {
            console.error(e);
        }
    };

    const handleSaveAlert = async (e) => {
        e.preventDefault();
        const payload = {
            ...alertForm,
            threshold: parseFloat(alertForm.threshold),
            created_by: user.username
        };
        if (!payload.comparison_column) delete payload.comparison_column;
        if (!payload.email_recipient) delete payload.email_recipient;
        if (!payload.webhook_url) delete payload.webhook_url;

        try {
            let res;
            if (currentAlert) {
                res = await fetch(`${API_BASE}/api/alerts/${currentAlert.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                res = await fetch(`${API_BASE}/api/alerts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }
            if (res.ok) {
                setAlertModalOpen(false);
                setCurrentAlert(null);
                setAlertForm({
                    name: "",
                    condition_type: "total_leakage_daily",
                    threshold: "",
                    comparison_column: "",
                    bot_type: "revenue",
                    email_recipient: "",
                    webhook_url: ""
                });
                setDryRunResults(null);
                fetchAlerts();
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleDryRunAlert = async () => {
        setDryRunLoading(true);
        setDryRunResults(null);
        try {
            const res = await fetch(`${API_BASE}/api/alerts/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    condition_type: alertForm.condition_type,
                    threshold: parseFloat(alertForm.threshold || 0),
                    comparison_column: alertForm.comparison_column || null,
                    bot_type: alertForm.bot_type,
                    username: user.username
                })
            });
            const data = await res.json();
            setDryRunResults(data.triggers || []);
        } catch (e) {
            console.error(e);
        } finally {
            setDryRunLoading(false);
        }
    };

    const handleRunAlertsCheckNow = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/alerts/check-now`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user.username })
            });
            if (res.ok) {
                alert("Triggered manual alert check! Pulling new notifications...");
                fetchNotifications();
                fetchUnreadCount();
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleMarkAsRead = async (notificationId) => {
        try {
            await fetch(`${API_BASE}/api/alerts/notifications/${notificationId}/read?username=${user.username}`, {
                method: 'POST'
            });
            fetchNotifications();
            fetchUnreadCount();
        } catch (e) {
            console.error(e);
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await Promise.all(notifications.filter(n => n.status === 'unread').map(n => 
                fetch(`${API_BASE}/api/alerts/notifications/${n.id}/read?username=${user.username}`, { method: 'POST' })
            ));
            fetchNotifications();
            fetchUnreadCount();
        } catch (e) {
            console.error(e);
        }
    };

    const handleViewNotificationDetails = (notification) => {
        setNotificationPanelOpen(false);
        setBot(notification.bot_type);
        setClickedBarName(notification.triggered_at.split(' ')[0]);
        setClickedBarQuery(notification.alert_name);
        setDrawerOpen(true);
        setDrawerLoading(true);
        setDrawerTab('transactions');
        setDrawerData(null);

        const triggerDate = notification.triggered_at.split(' ')[0];

        let url = `${API_BASE}/transactions?bot=${notification.bot_type}&query=`;
        if (notification.condition_type === 'total_leakage_daily' || notification.condition_type === 'surgery_loss' || notification.condition_type === 'unbilled_rate') {
            url += `month&value=${encodeURIComponent(triggerDate)}`;
        } else if (notification.condition_type === 'department_leakage') {
            url += `location&value=${encodeURIComponent(notification.comparison_column)}&start_date=${triggerDate}&end_date=${triggerDate}`;
        }

        fetch(url)
            .then(res => res.json())
            .then(data => {
                setDrawerData(data);
            })
            .catch(console.error)
            .finally(() => {
                setDrawerLoading(false);
            });

        handleMarkAsRead(notification.id);
    };

    // Alerts fetch on mount & theme pull
    useEffect(() => {
        if (user) {
            fetchAlerts();
            fetchNotifications();
            fetchUnreadCount();
        }
    }, [user, bot]);

    // Live unread badge count polling
    useEffect(() => {
        if (!user) return;
        const interval = setInterval(() => {
            fetchUnreadCount();
        }, 15000);
        return () => clearInterval(interval);
    }, [user]);

    
    // Core Workflow Data
    const [messages, setMessages] = useState({ revenue: [], audit: [] });
    const [locations, setLocations] = useState([]);
    const [filters, setFilters] = useState({ period: 'all', start: '', end: '', location: '' });
    
    // Compare Mode & Feedback States
    const [compareMode, setCompareMode] = useState(false);
    const [filtersB, setFiltersB] = useState({ period: 'all', start: '', end: '', location: '' });
    const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [feedbackMsg, setFeedbackMsg] = useState(null);
    const [feedbackType, setFeedbackType] = useState('Wrong numbers');
    const [feedbackComment, setFeedbackComment] = useState('');
    const [sessions, setSessions] = useState([]);
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const [isTyping, setIsTyping] = useState(false);
    const [followUpSuggestions, setFollowUpSuggestions] = useState([]);
    
    // Input / Autocomplete States
    const [queryInput, setQueryInput] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    
    // Drag & Drop / Upload Progress State
    const [dragActive, setDragActive] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({ state: 'idle', message: '' });

    // Drawer States for Clicked Chart Bars
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [drawerData, setDrawerData] = useState(null);
    const [drawerLoading, setDrawerLoading] = useState(false);
    const [drawerTab, setDrawerTab] = useState('transactions'); // 'transactions' | 'staff' | 'trend'
    const [clickedBarName, setClickedBarName] = useState('');
    const [clickedBarQuery, setClickedBarQuery] = useState('');

    const chatFeedEndRef = useRef(null);
    const debounceRef = useRef(null);

    const handleLogout = async (reason = 'User clicked Sign Out') => {
        try {
            await fetch(`${API_BASE}/audit-logs/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user?.username || 'Unknown',
                    action_type: 'LOGOUT',
                    details: { reason }
                })
            });
        } catch (e) {
            console.error("Failed to log logout event:", e);
        }
        setUser(null);
    };

    const handleFeedbackSubmit = async (msg, msgIdx, type, comment = '') => {
        try {
            let userQuery = "Unknown Query";
            const botMsgs = messages[bot];
            if (botMsgs && msgIdx > 0 && botMsgs[msgIdx - 1].role === 'user') {
                userQuery = botMsgs[msgIdx - 1].text;
            }

            await fetch(`${API_BASE}/feedback/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    query: userQuery,
                    bot_response: typeof msg.text === 'string' ? msg.text : JSON.stringify(msg),
                    feedback_type: type,
                    comment: comment || null,
                    user_id: user?.username || 'Unknown'
                })
            });

            setMessages(prev => {
                const list = [...prev[bot]];
                list[msgIdx] = { ...list[msgIdx], feedbackSubmitted: type };
                return { ...prev, [bot]: list };
            });
        } catch (e) {
            console.error("Failed to submit feedback:", e);
        }
    };

    // Inactivity Timeout Hook (Auto-logout after 15 minutes)
    useEffect(() => {
        if (!user) return;

        let timeoutId;
        const TIMEOUT_DURATION = 15 * 60 * 1000; // 15 minutes

        const triggerAutoLogout = () => {
            handleLogout('Inactivity timeout');
            alert("Your session has expired due to 15 minutes of inactivity. Please authenticate again.");
        };

        const resetTimer = () => {
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(triggerAutoLogout, TIMEOUT_DURATION);
        };

        const events = ['mousemove', 'keydown', 'click', 'scroll'];
        events.forEach(e => window.addEventListener(e, resetTimer));

        resetTimer();

        return () => {
            if (timeoutId) clearTimeout(timeoutId);
            events.forEach(e => window.removeEventListener(e, resetTimer));
        };
    }, [user]);

    // Live Filter Change Ingestion Tracking
    const isInitialFilterRef = useRef(true);
    useEffect(() => {
        if (!user) return;
        if (isInitialFilterRef.current) {
            isInitialFilterRef.current = false;
            return;
        }

        fetch(`${API_BASE}/audit-logs/log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.username,
                action_type: 'FILTER_CHANGED',
                details: {
                    period: filters.period,
                    start: filters.start,
                    end: filters.end,
                    location: filters.location
                }
            })
        }).catch(err => console.error("Failed to log filter change:", err));
    }, [filters]);

    // Initial theme attribute hook
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('amrita-theme', theme);
    }, [theme]);

    // Fetch master locations
    useEffect(() => {
        fetch(`${API_BASE}/locations`)
            .then(r => r.json())
            .then(data => setLocations(data.locations || []))
            .catch(console.error);
    }, []);

    // Fetch real-time dashboard KPIs on mount and every 30 seconds
    useEffect(() => {
        const fetchKpis = async () => {
            try {
                const res = await fetch(`${API_BASE}/dashboard/kpis`);
                if (res.ok) {
                    const data = await res.json();
                    setKpis(data);
                }
            } catch (err) {
                console.error("Error fetching KPIs:", err);
            }
        };
        fetchKpis();
        const interval = setInterval(fetchKpis, 30000);
        return () => clearInterval(interval);
    }, []);

    // Active Bot or User updates trigger session pulls
    useEffect(() => {
        if (user) {
            fetchSessions(bot);
            setCurrentSessionId(null);
            setMessages(prev => ({ ...prev, [bot]: [] }));
            setFollowUpSuggestions([]);
        }
    }, [bot, user]);

    // Scroll to bottom on new messages or typing state changes
    useEffect(() => {
        if (chatFeedEndRef.current) {
            chatFeedEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isTyping]);

    // Autocomplete Trigger hook
    useEffect(() => {
        if (!queryInput.trim()) {
            setSuggestions([]);
            return;
        }
        
        if (debounceRef.current) clearTimeout(debounceRef.current);
        
        debounceRef.current = setTimeout(() => {
            fetchSuggestions(queryInput);
        }, 250);
    }, [queryInput, bot]);

    // Global Key Listener for ⌘K Command Palette
    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setCommandBarOpen(prev => !prev);
            }
            if (e.key === 'Escape') {
                setCommandBarOpen(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const toggleTheme = () => {
        setTheme(t => t === 'dark' ? 'light' : 'dark');
    };

    const fetchSessions = async (activeBot) => {
        if (!user) return;
        try {
            const res = await fetch(`${API_BASE}/sessions/${activeBot}?username=${user.username}`);
            const data = await res.json();
            setSessions(data.sessions || []);
        } catch (e) {
            console.error(e);
        }
    };

    const loadSession = async (sessionId) => {
        try {
            const res = await fetch(`${API_BASE}/history/${sessionId}`);
            const data = await res.json();
            setCurrentSessionId(sessionId);
            setMessages(prev => ({ ...prev, [bot]: data.messages || [] }));
            setFollowUpSuggestions([]);
        } catch (e) {
            console.error(e);
        }
    };

    const handleNewChat = () => {
        setCurrentSessionId(null);
        setMessages(prev => ({ ...prev, [bot]: [] }));
        setFollowUpSuggestions([]);
        fetchSessions(bot);
    };

    const addMessage = (botName, msg) => {
        setMessages(prev => ({
            ...prev,
            [botName]: [...prev[botName], msg]
        }));
    };

    const handleSend = async (queryText, locationFilter = null, overrideBot = null) => {
        if (!queryText.trim()) return;

        const activeBot = overrideBot || bot;

        // Clear existing suggestions
        setFollowUpSuggestions([]);

        addMessage(activeBot, { role: 'user', text: queryText });
        
        // Add a placeholder streaming bot message that we can append tokens to
        addMessage(activeBot, { role: 'bot', text: '', streaming: true });
        
        setQueryInput('');
        setShowSuggestions(false);
        setIsTyping(false); // Turn off generic typing spinner since streaming is inline

        const targetLocation = locationFilter || filters.location || null;

        if (compareMode) {
            try {
                const res = await fetch(`${API_BASE}/chat/compare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: queryText,
                        bot: activeBot,
                        username: user.username,
                        session_id: currentSessionId,
                        period_a: {
                            start_date: filters.start || null,
                            end_date: filters.end || null,
                            location_filter: targetLocation
                        },
                        period_b: {
                            start_date: filtersB.start || null,
                            end_date: filtersB.end || null,
                            location_filter: filtersB.location || targetLocation
                        }
                    })
                });

                if (!res.ok) {
                    throw new Error("HTTP error " + res.status);
                }

                const payload = await res.json();
                
                if (payload.error) {
                    setMessages(prev => {
                        const botMsgs = [...prev[activeBot]];
                        const lastIdx = botMsgs.length - 1;
                        if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                            botMsgs[lastIdx] = {
                                role: 'bot',
                                text: payload.error,
                                streaming: false
                            };
                        }
                        return { ...prev, [activeBot]: botMsgs };
                    });
                    return;
                }

                setMessages(prev => {
                    const botMsgs = [...prev[activeBot]];
                    const lastIdx = botMsgs.length - 1;
                    if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                        botMsgs[lastIdx] = {
                            ...botMsgs[lastIdx],
                            isCompare: true,
                            textA: payload.period_a.answer,
                            textB: payload.period_b.answer,
                            chart: payload.chart_data,
                            chartType: payload.chart_type,
                            chartValueType: payload.chart_value_type,
                            deltas: payload.deltas,
                            period_a_kpis: payload.period_a.kpis,
                            period_b_kpis: payload.period_b.kpis,
                            streaming: false
                        };
                    }
                    return { ...prev, [activeBot]: botMsgs };
                });

                if (!currentSessionId && payload.session_id) {
                    setCurrentSessionId(payload.session_id);
                    fetchSessions(activeBot);
                }

                setFollowUpSuggestions(
                    activeBot === 'revenue' 
                        ? ["Show monthly trend", "Compare departments"]
                        : ["Show surgeon package breakdown", "Contrast by specialty"]
                );

            } catch (e) {
                console.error("Compare reader failed:", e);
                setMessages(prev => {
                    const botMsgs = [...prev[activeBot]];
                    const lastIdx = botMsgs.length - 1;
                    if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                        botMsgs[lastIdx] = {
                            role: 'bot',
                            text: 'Error connecting to the server for comparison. Please verify API is running.',
                            streaming: false
                        };
                    }
                    return { ...prev, [activeBot]: botMsgs };
                });
            }
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/chat/stream/${activeBot}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: queryText,
                    bot: activeBot,
                    username: user.username,
                    session_id: currentSessionId,
                    start_date: filters.start || null,
                    end_date: filters.end || null,
                    location_filter: targetLocation
                })
            });

            if (!res.ok) {
                throw new Error("HTTP error " + res.status);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            let fullText = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop(); // Save last incomplete line to buffer

                for (const line of lines) {
                    const cleaned = line.trim();
                    if (cleaned.startsWith("data: ")) {
                        const dataStr = cleaned.slice(6).trim();
                        if (dataStr) {
                            try {
                                const payload = JSON.parse(dataStr);
                                if (payload.done) {
                                    // Update streaming message with final answer, charts and done status
                                    setMessages(prev => {
                                        const botMsgs = [...prev[activeBot]];
                                        const lastIdx = botMsgs.length - 1;
                                        if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                                            botMsgs[lastIdx] = {
                                                ...botMsgs[lastIdx],
                                                text: fullText,
                                                chart: payload.chart_data,
                                                chartType: payload.chart_type,
                                                chartValueType: payload.chart_value_type,
                                                streaming: false
                                            };
                                        }
                                        return { ...prev, [activeBot]: botMsgs };
                                    });

                                    if (!currentSessionId && payload.session_id) {
                                        setCurrentSessionId(payload.session_id);
                                        fetchSessions(activeBot);
                                    }

                                    if (payload.follow_up_suggestions) {
                                        setFollowUpSuggestions(payload.follow_up_suggestions);
                                    }
                                } else if (payload.text) {
                                    fullText += payload.text;
                                    setMessages(prev => {
                                        const botMsgs = [...prev[activeBot]];
                                        const lastIdx = botMsgs.length - 1;
                                        if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                                            botMsgs[lastIdx] = {
                                                ...botMsgs[lastIdx],
                                                text: fullText
                                            };
                                        }
                                        return { ...prev, [activeBot]: botMsgs };
                                    });
                                }
                            } catch (e) {
                                console.error("Error parsing stream chunk:", e);
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Stream reader failed:", e);
            setMessages(prev => {
                const botMsgs = [...prev[activeBot]];
                const lastIdx = botMsgs.length - 1;
                if (lastIdx >= 0 && botMsgs[lastIdx].role === 'bot') {
                    botMsgs[lastIdx] = {
                        role: 'bot',
                        text: 'Error connecting to the server. Please verify API is running and streaming is active.',
                        streaming: false
                    };
                }
                return { ...prev, [activeBot]: botMsgs };
            });
        }
    };

    const fetchSuggestions = async (q) => {
        try {
            const res = await fetch(`${API_BASE}/autocomplete?q=${encodeURIComponent(q)}&bot=${bot}`);
            const data = await res.json();
            setSuggestions(data.suggestions || []);
        } catch (e) {
            console.error(e);
        }
    };

    const handleSelectSuggestion = (suggestion) => {
        // Extract location if injected (e.g. "Which floor... - ICU")
        let loc = null;
        if (suggestion.includes('- ')) {
            const parts = suggestion.split('- ');
            loc = parts[parts.length - 1].replace('?', '').trim();
        }
        handleSend(suggestion, loc);
    };

    // File Ingestion Handler
    const handleFileUpload = async (file) => {
        if (!file) return;
        setUploadProgress({ state: 'loading', message: `Uploading ${file.name}...` });
        
        const fd = new FormData();
        fd.append('file', file);
        try {
            const res = await fetch(`${API_BASE}/upload?username=${encodeURIComponent(user.username)}`, { 
                method: 'POST', 
                body: fd 
            });
            if (!res.ok) throw new Error("Server rejected file upload");
            setUploadProgress({ state: 'success', message: `${file.name} ingested successfully!` });
            setTimeout(() => setUploadProgress({ state: 'idle', message: '' }), 5000);
        } catch (err) {
            setUploadProgress({ state: 'error', message: 'Ingestion failed. Try Excel/PDF files.' });
            setTimeout(() => setUploadProgress({ state: 'idle', message: '' }), 5000);
        }
    };

    // Drag and Drop listeners
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    };



    // Handler when a user clicks a bar on any BarChart
    const handleBarClick = async (entry, msg) => {
        if (!entry || !entry.name) return;
        
        setClickedBarName(entry.name);
        setClickedBarQuery(msg.text);
        
        // Log chart drilldown action for compliance
        fetch(`${API_BASE}/audit-logs/log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.username,
                action_type: 'CHART_DRILLDOWN',
                details: {
                    bar_name: entry.name,
                    query: msg.text,
                    active_filters: filters
                }
            })
        }).catch(err => console.error("Failed to log chart drilldown:", err));
        setDrawerOpen(true);
        setDrawerLoading(true);
        setDrawerTab('transactions');
        setDrawerData(null);
        
        try {
            const url = `${API_BASE}/transactions?bot=${bot}&query=${encodeURIComponent(msg.text)}&value=${encodeURIComponent(entry.name)}&start_date=${filters.start || ''}&end_date=${filters.end || ''}&location_filter=${filters.location || ''}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error("Failed to fetch transaction details");
            const data = await res.json();
            setDrawerData(data);
        } catch (err) {
            console.error(err);
        } finally {
            setDrawerLoading(false);
        }
    };

    // Prefills chat text box and highlights it
    const handleAskAboutThis = () => {
        setDrawerOpen(false);
        const question = `Tell me more about ${clickedBarName} leakage`;
        setQueryInput(question);
        
        setTimeout(() => {
            const inputEl = document.querySelector('.chat-input');
            if (inputEl) {
                inputEl.focus();
            }
        }, 100);
    };

    const formatCompactCurrency = (val) => {
        if (val >= 10000000) {
            return '₹' + (val / 10000000).toFixed(2) + ' Cr';
        } else if (val >= 100000) {
            return '₹' + (val / 100000).toFixed(2) + ' L';
        }
        return '₹' + Math.round(val).toLocaleString('en-IN');
    };

    const handleTileClick = (tileType) => {
        if (tileType === 'total_leakage') {
            setBot('revenue');
            handleSend("What is the total revenue leakage and breakdown by service?", null, 'revenue');
        } else if (tileType === 'unbilled_rate') {
            setBot('revenue');
            handleSend("What is the average unbilled rate and percentage?", null, 'revenue');
        } else if (tileType === 'top_offending_dept') {
            const dept = kpis.top_offending_dept;
            const isSurgerySpeciality = dept.toLowerCase().includes('surgery') || 
                                        dept.toLowerCase().includes('cardio') || 
                                        dept.toLowerCase().includes('ortho') || 
                                        dept.toLowerCase().includes('urology') || 
                                        dept.toLowerCase().includes('ent') || 
                                        dept.toLowerCase().includes('obg');
            const targetBot = isSurgerySpeciality ? 'audit' : 'revenue';
            setBot(targetBot);
            handleSend(`Show me detailed leakage breakdown for ${dept}`, null, targetBot);
        } else if (tileType === 'surgery_audit_loss') {
            setBot('audit');
            handleSend("What is the total surgery audit loss?", null, 'audit');
        }
    };

    // Client-side CSV Download Exporter
    const exportToCsv = (data, filename) => {
        if (!data || data.length === 0) return;
        const headers = ['Date', 'Patient ID', 'Item Name', 'Amount (INR)', 'Staff/Surgeon', 'Location/Speciality'];
        const rows = data.map(t => [
            t.date,
            t.patient_id,
            t.service_name || '',
            t.leakage_amount || 0,
            t.staff_name || '',
            t.location || ''
        ]);
        
        const csvContent = "data:text/csv;charset=utf-8," 
            + [headers.join(','), ...rows.map(e => e.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Client-side Chart-to-PNG Exporter using html-to-image
    const exportChartAsPng = (e, index) => {
        e.stopPropagation();
        const container = e.currentTarget.closest('.recharts-responsive-container');
        if (!container) return;
        
        const btn = container.querySelector('.chart-export-btn');
        if (btn) btn.style.display = 'none';
        
        window.htmlToImage.toPng(container, {
            backgroundColor: theme === 'dark' ? '#1A1B26' : '#FDF6E3',
            style: {
                padding: '12px',
                borderRadius: '12px'
            }
        })
        .then((dataUrl) => {
            if (btn) btn.style.display = 'flex';
            const link = document.createElement('a');
            link.download = `chart_${bot}_${index + 1}.png`;
            link.href = dataUrl;
            link.click();
        })
        .catch((error) => {
            if (btn) btn.style.display = 'flex';
            console.error('oops, something went wrong with chart export!', error);
        });
    };

    const renderMessageBubble = (msg, idx, lane) => {
        let isCompare = msg.isCompare || msg.chartType === 'bar_compare' || msg.chart_type === 'bar_compare';
        let text = msg.text;
        if (isCompare) {
            if (msg.textA !== undefined) {
                text = lane === 'B' ? msg.textB : msg.textA;
            } else {
                try {
                    const parsed = JSON.parse(msg.text);
                    text = lane === 'B' ? parsed.text_b : parsed.text_a;
                } catch (e) {
                    text = msg.text;
                }
            }
        }

        if (msg.role === 'user') {
            return (
                <div key={idx} className="message-bubble message-user" style={{ alignSelf: 'flex-end', marginBottom: '12px' }}>
                    <p>{msg.text}</p>
                </div>
            );
        }

        return (
            <div key={idx} className="message-bubble message-bot animate-fadeIn" style={{ alignSelf: 'flex-start', marginBottom: '12px', width: '100%' }}>
                <p style={{ whiteSpace: 'pre-wrap' }}>
                    {text}
                    {msg.streaming && <span className="streaming-cursor">|</span>}
                </p>

                {msg.chart && msg.chart.length > 0 && (
                    <div className="recharts-responsive-container" style={{ position: 'relative', marginTop: '12px' }}>
                        <button 
                            className="chart-export-btn absolute top-3 right-3 p-1.5 rounded-lg bg-[var(--card-background)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:border-[var(--accent)] transition-all z-10 flex items-center justify-center"
                            title="Export Chart as PNG"
                            onClick={(e) => exportChartAsPng(e, idx)}
                            style={{ cursor: 'pointer' }}
                        >
                            <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                        </button>

                        <div style={{ height: '240px', width: '100%' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={msg.chart} margin={{ top: 25, right: 10, left: 10, bottom: 35 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGridColor} />
                                    <XAxis 
                                        dataKey="name" 
                                        axisLine={false} 
                                        tickLine={false} 
                                        tick={{ fill: chartTextColor, fontSize: 10 }} 
                                        interval={0}
                                        angle={-25}
                                        textAnchor="end"
                                        height={55}
                                    />
                                    <YAxis 
                                        width={65} 
                                        axisLine={false} 
                                        tickLine={false} 
                                        tick={{ fill: chartTextColor, fontSize: 11 }} 
                                        tickFormatter={(val) => msg.chartValueType === 'count' ? val : '₹' + Intl.NumberFormat('en-IN', { notation: "compact", compactDisplay: "short" }).format(val)} 
                                    />
                                    <Tooltip 
                                        cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} 
                                        formatter={(value, name) => {
                                            const label = isCompare ? (name === 'period_a' ? 'Period A' : 'Period B') : 'Amount';
                                            return msg.chartValueType === 'count' ? [value, label] : ['₹' + value.toLocaleString('en-IN'), label];
                                        }}
                                        contentStyle={{ 
                                            backgroundColor: 'var(--card-background)', 
                                            borderColor: 'var(--border)', 
                                            color: 'var(--text-primary)',
                                            borderRadius: '8px'
                                        }} 
                                    />
                                    {isCompare ? (
                                        <>
                                            <Bar 
                                                dataKey="period_a" 
                                                name="Period A"
                                                fill="#7AA2F7" 
                                                radius={[4, 4, 0, 0]}
                                                onClick={(entry) => handleBarClick(entry, msg)}
                                            />
                                            <Bar 
                                                dataKey="period_b" 
                                                name="Period B"
                                                fill="#9ECE6A" 
                                                radius={[4, 4, 0, 0]}
                                                onClick={(entry) => handleBarClick(entry, msg)}
                                            />
                                        </>
                                    ) : (
                                        <Bar 
                                            dataKey="leakage" 
                                            fill={chartAccentColor} 
                                            radius={[4, 4, 0, 0]}
                                            onClick={(entry) => handleBarClick(entry, msg)}
                                        >
                                            {msg.chart.map((entry, index) => (
                                                <Cell 
                                                    key={`cell-${index}`} 
                                                    fill={chartAccentColor} 
                                                    style={{ cursor: 'pointer' }}
                                                    className="hover:opacity-80 transition-opacity"
                                                />
                                            ))}
                                        </Bar>
                                    )}
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {!msg.streaming && text && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '12px', paddingTop: '8px', borderTop: '1px solid var(--border)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        {msg.feedbackSubmitted ? (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--success)', fontWeight: '500' }}>
                                <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                </svg>
                                {msg.feedbackSubmitted === 'thumbs_up' ? 'Helpful response registered' : 'Issue reported: ' + msg.feedbackSubmitted}
                            </span>
                        ) : (
                            <>
                                <span>Was this response helpful?</span>
                                <button 
                                    onClick={() => handleFeedbackSubmit(msg, idx, 'thumbs_up')} 
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', padding: '2px', borderRadius: '4px' }}
                                    className="hover:bg-[rgba(158,206,106,0.15)]"
                                    title="Helpful"
                                >
                                    👍
                                </button>
                                <button 
                                    onClick={() => {
                                        setFeedbackMsg({ msg, idx });
                                        setFeedbackType('Wrong numbers');
                                        setFeedbackComment('');
                                        setFeedbackModalOpen(true);
                                    }} 
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', padding: '2px', borderRadius: '4px' }}
                                    className="hover:bg-[rgba(247,118,142,0.15)]"
                                    title="Unhelpful"
                                >
                                    👎
                                </button>
                            </>
                        )}
                    </div>
                )}
            </div>
        );
    };

    if (!user) {
        return <Login onLogin={u => {
            setUser(u);
            if (u.bots && u.bots.length > 0) setBot(u.bots[0]);
        }} />;
    }

    // Colors mapping to active state variables for Recharts theme adaptation
    const isDark = theme === 'dark';
    const chartAccentColor = isDark ? '#7AA2F7' : '#CB4B16';
    const chartGridColor = isDark ? '#2D3A5E' : '#E9E1C7';
    const chartTextColor = isDark ? '#787C99' : '#586E75';

    const lastMsg = messages[bot] ? messages[bot][messages[bot].length - 1] : null;
    let activeDeltas = null;
    if (lastMsg) {
        if (lastMsg.isCompare) {
            activeDeltas = lastMsg.deltas;
        } else if (lastMsg.chartType === 'bar_compare' || lastMsg.chart_type === 'bar_compare') {
            try {
                const parsed = JSON.parse(lastMsg.text);
                activeDeltas = parsed.deltas;
            } catch (e) {
                console.error("Failed to parse historical compare deltas:", e);
            }
        }
    }



    // Contextual Quick-Start suggestions based on bot
    const emptyQueries = bot === 'revenue' ? [
        { title: "Service Leakage Areas", q: "Which services or charges are most frequently missed in billing?" },
        { title: "Highest Leakage Department", q: "Which floor or department has the highest revenue leakage?" },
        { title: "Monthly Trends Breakdown", q: "Which month or time period shows the highest revenue leakage trends?" },
        { title: "Staff Underbilling Patterns", q: "Which staff members are linked to the most unbilled charges?" }
    ] : [
        { title: "Total Audit Discrepancies", q: "What is the total surgery audit loss and discrepancies?" },
        { title: "Speciality Discrepancy Splits", q: "Show the top surgical specialty losses in audit logs" },
        { title: "Highest Discrepancy Doctors", q: "Which surgeons or doctors are linked to the worst surgery package discrepancies?" },
        { title: "Timeline Discrepancies", q: "Show monthly surgery package audit losses and trends" }
    ];

    return (
        <div className="app-container" style={{ gridTemplateColumns: (bot === 'audit_logs' || bot === 'alerts') ? '280px 1fr' : undefined }}>
            {/* COLUMN 1: LEFT SIDEBAR */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1 className="sidebar-title">Amrita Guard</h1>
                    <div className="sidebar-subtitle">Analytics Control Room</div>
                </div>

                <div className="bot-toggle-group">
                    {user.bots.includes('revenue') && (
                        <button 
                            className={`bot-toggle-btn ${bot === 'revenue' ? 'active' : ''}`}
                            onClick={() => setBot('revenue')}
                        >
                            <span>💰</span> Revenue Leakage
                        </button>
                    )}
                    {user.bots.includes('audit') && (
                        <button 
                            className={`bot-toggle-btn ${bot === 'audit' ? 'active' : ''}`}
                            onClick={() => setBot('audit')}
                        >
                            <span>🏥</span> Surgery Audit
                        </button>
                    )}
                    {user.username === 'Admin' && (
                        <button 
                            className={`bot-toggle-btn ${bot === 'audit_logs' ? 'active' : ''}`}
                            onClick={() => setBot('audit_logs')}
                        >
                            <span>📋</span> Audit Compliance
                        </button>
                    )}
                    {user.username === 'Admin' && (
                        <button 
                            className={`bot-toggle-btn ${bot === 'alerts' ? 'active' : ''}`}
                            onClick={() => setBot('alerts')}
                            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}
                        >
                            <span style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>🚨 Alerts Management</span>
                            {unreadCount > 0 && (
                                <span style={{
                                    backgroundColor: 'var(--danger)',
                                    color: 'white',
                                    fontSize: '10px',
                                    fontWeight: 'bold',
                                    borderRadius: '50%',
                                    padding: '2px 6px',
                                    lineHeight: '1'
                                }}>
                                    {unreadCount}
                                </span>
                            )}
                        </button>
                    )}
                </div>


                <button className="new-chat-btn" onClick={handleNewChat}>
                    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                    New Consultation
                </button>

                <div className="session-section-title">Consultations</div>
                <div className="sessions-list">
                    {sessions.map(s => (
                        <button 
                            key={s.session_id}
                            className={`session-item ${currentSessionId === s.session_id ? 'active' : ''}`}
                            onClick={() => loadSession(s.session_id)}
                        >
                            <span className="session-title">{s.title || "Consultation Details"}</span>
                        </button>
                    ))}
                    {sessions.length === 0 && (
                        <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center' }}>
                            No prior histories
                        </div>
                    )}
                </div>

                <footer className="sidebar-footer">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 8px 8px 8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success)' }}></div>
                        <span style={{ fontWeight: '500' }}>Active: {user.username}</span>
                    </div>
                    <button className="logout-btn" onClick={() => handleLogout()}>
                        Sign Out
                    </button>
                </footer>
            </aside>

            {/* COLUMN 2: WORKSPACE & INTERACTIVE CHAT AREA */}
            <main className="workspace">
                {/* Top Nav Header */}
                <header className="workspace-header">
                    <div className="header-left">
                        <h2 className="header-title">
                            {bot === 'revenue' ? 'Revenue Leakage Control' : bot === 'audit' ? 'Surgery Audit Registry' : bot === 'alerts' ? 'Alerts Management Dashboard' : 'Audit Compliance Registry'}
                        </h2>
                        <div className="header-meta">
                            {bot === 'alerts' ? 'Automated Incident Monitors' : bot === 'audit_logs' ? 'Compliance Operations' : currentSessionId ? `Session ID: ${currentSessionId}` : 'New Workspace Consultation'}
                        </div>
                    </div>

                    <div className="header-actions">
                        {user.username === 'Admin' && (
                            <div style={{ position: 'relative' }}>
                                <button className="notification-bell-btn" onClick={() => setNotificationPanelOpen(!notificationPanelOpen)} title="Alert Notifications">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
                                    </svg>
                                    {unreadCount > 0 && (
                                        <span className="bell-badge">
                                            {unreadCount}
                                        </span>
                                    )}
                                </button>
                                {notificationPanelOpen && (
                                    <div className="notification-panel">
                                        <div className="notification-panel-header">
                                            <span className="notification-panel-title">System Alerts</span>
                                            <button className="notification-panel-clear" onClick={handleMarkAllAsRead}>
                                                Mark all read
                                            </button>
                                        </div>
                                        <div className="notification-list">
                                            {notifications.length === 0 ? (
                                                <div className="notification-empty">No active notifications</div>
                                            ) : (
                                                notifications.map(n => (
                                                    <div 
                                                        key={n.id} 
                                                        className={`notification-item ${n.status === 'unread' ? 'unread' : ''}`}
                                                        onClick={() => handleViewNotificationDetails(n)}
                                                    >
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span className="notification-item-title">{n.alert_name}</span>
                                                            <span style={{
                                                                fontSize: '9px',
                                                                fontWeight: 'bold',
                                                                textTransform: 'uppercase',
                                                                color: n.bot_type === 'revenue' ? 'var(--accent)' : 'var(--warning)',
                                                                backgroundColor: 'rgba(45, 58, 94, 0.2)',
                                                                padding: '2px 6px',
                                                                borderRadius: '4px'
                                                            }}>
                                                                {n.bot_type}
                                                            </span>
                                                        </div>
                                                        <span className="notification-item-desc">
                                                            Value detected: <strong style={{ color: 'var(--danger)' }}>
                                                                {n.condition_type === 'unbilled_rate' ? '' : '₹'}{n.value_detected.toLocaleString('en-IN')}{n.condition_type === 'unbilled_rate' ? '%' : ''}
                                                            </strong> (Threshold: {n.condition_type === 'unbilled_rate' ? '' : '₹'}{n.threshold.toLocaleString('en-IN')}{n.condition_type === 'unbilled_rate' ? '%' : ''})
                                                        </span>
                                                        <div className="notification-item-meta">
                                                            <span>Target Date: {n.triggered_at.split(' ')[0]}</span>
                                                            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>View Details &rarr;</span>
                                                        </div>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                        <button className="command-bar-trigger" onClick={() => setCommandBarOpen(true)}>
                            <span>Search actions...</span>
                            <span className="kbd-pill">⌘K</span>
                        </button>
                        <button className="theme-toggle-btn" onClick={toggleTheme} title="Toggle Theme (Delhi Night / Bone Theme)">

                            {isDark ? (
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
                            ) : (
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
                            )}
                        </button>
                    </div>
                </header>

                {bot === 'audit_logs' ? (
                    <AuditLogsView user={user} API_BASE={API_BASE} />
                ) : bot === 'alerts' ? (
                    <AlertsView 
                        user={user}
                        API_BASE={API_BASE}
                        locations={locations}
                        alerts={alerts}
                        fetchAlerts={fetchAlerts}
                        alertModalOpen={alertModalOpen}
                        setAlertModalOpen={setAlertModalOpen}
                        currentAlert={currentAlert}
                        setCurrentAlert={setCurrentAlert}
                        alertForm={alertForm}
                        setAlertForm={setAlertForm}
                        dryRunResults={dryRunResults}
                        setDryRunResults={setDryRunResults}
                        dryRunLoading={dryRunLoading}
                        setDryRunLoading={setDryRunLoading}
                        handleToggleAlertActive={handleToggleAlertActive}
                        handleDeleteAlert={handleDeleteAlert}
                        handleSaveAlert={handleSaveAlert}
                        handleDryRunAlert={handleDryRunAlert}
                        handleRunAlertsCheckNow={handleRunAlertsCheckNow}
                    />
                ) : (

                    <>
                        {/* Sticky KPI Row */}
                        {compareMode ? (
                            <section className="kpi-row" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                                <div className="kpi-tile">
                                    <div className="kpi-title">{bot === 'revenue' ? 'Revenue Leakage Compare (₹)' : 'Surgery Audit Loss Compare (₹)'}</div>
                                    {activeDeltas ? (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                                            <div>
                                                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Period A</div>
                                                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{formatCompactCurrency(activeDeltas.total_loss.val_a)}</div>
                                            </div>
                                            <div style={{
                                                backgroundColor: activeDeltas.total_loss.pct_change > 0 ? 'rgba(247, 118, 142, 0.15)' : 'rgba(158, 206, 106, 0.15)',
                                                color: activeDeltas.total_loss.pct_change > 0 ? 'var(--danger)' : 'var(--success)',
                                                fontSize: '11px',
                                                fontWeight: 'bold',
                                                padding: '4px 10px',
                                                borderRadius: '20px'
                                            }}>
                                                {activeDeltas.total_loss.pct_change > 0 ? '▲' : '▼'} {Math.abs(activeDeltas.total_loss.pct_change)}%
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Period B</div>
                                                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{formatCompactCurrency(activeDeltas.total_loss.val_b)}</div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '12px' }}>
                                            Submit comparative query to view deltas
                                        </div>
                                    )}
                                    <div className="kpi-desc" style={{ marginTop: '8px' }}><span>📊</span> Period-over-period leakage metrics</div>
                                </div>

                                <div className="kpi-tile">
                                    <div className="kpi-title">{bot === 'revenue' ? 'Unbilled Cases Compare' : 'Surgical Discrepancies Compare'}</div>
                                    {activeDeltas ? (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                                            <div>
                                                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Period A</div>
                                                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                                                    {bot === 'revenue' ? activeDeltas.unbilled_cases.val_a : activeDeltas.total_discrepancies.val_a}
                                                </div>
                                            </div>
                                            <div style={{
                                                backgroundColor: (bot === 'revenue' ? activeDeltas.unbilled_cases.pct_change : activeDeltas.total_discrepancies.pct_change) > 0 ? 'rgba(247, 118, 142, 0.15)' : 'rgba(158, 206, 106, 0.15)',
                                                color: (bot === 'revenue' ? activeDeltas.unbilled_cases.pct_change : activeDeltas.total_discrepancies.pct_change) > 0 ? 'var(--danger)' : 'var(--success)',
                                                fontSize: '11px',
                                                fontWeight: 'bold',
                                                padding: '4px 10px',
                                                borderRadius: '20px'
                                            }}>
                                                {(bot === 'revenue' ? activeDeltas.unbilled_cases.pct_change : activeDeltas.total_discrepancies.pct_change) > 0 ? '▲' : '▼'} {Math.abs(bot === 'revenue' ? activeDeltas.unbilled_cases.pct_change : activeDeltas.total_discrepancies.pct_change)}%
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Period B</div>
                                                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                                                    {bot === 'revenue' ? activeDeltas.unbilled_cases.val_b : activeDeltas.total_discrepancies.val_b}
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '12px' }}>
                                            Submit comparative query to view deltas
                                        </div>
                                    )}
                                    <div className="kpi-desc" style={{ marginTop: '8px' }}><span>⚠️</span> Temporal discrepancy trends</div>
                                </div>
                            </section>
                        ) : (
                            <section className="kpi-row">
                                <div className="kpi-tile" onClick={() => handleTileClick('total_leakage')}>
                                    <div className="kpi-title">Total Leakage (₹)</div>
                                    <div className="kpi-value">{formatCompactCurrency(kpis.total_leakage)}</div>
                                    <div className="kpi-desc"><span>⚠️</span> Critical billing misses</div>
                                </div>
                                <div className="kpi-tile" onClick={() => handleTileClick('unbilled_rate')}>
                                    <div className="kpi-title">Unbilled Rate (%)</div>
                                    <div className="kpi-value">{kpis.unbilled_rate.toFixed(1)}%</div>
                                    <div className="kpi-desc"><span>📉</span> Unbilled charges ratio</div>
                                </div>
                                <div className="kpi-tile" onClick={() => handleTileClick('top_offending_dept')}>
                                    <div className="kpi-title">Top Offending Dept</div>
                                    <div className="kpi-value" style={{ fontSize: kpis.top_offending_dept.length > 15 ? '16px' : '22px', transition: 'all 0.3s ease' }}>
                                        {kpis.top_offending_dept}
                                    </div>
                                    <div className="kpi-desc"><span>🔴</span> {formatCompactCurrency(kpis.top_offending_dept_amount)} leakage</div>
                                </div>
                                <div className="kpi-tile" onClick={() => handleTileClick('surgery_audit_loss')}>
                                    <div className="kpi-title">Surgery Audit Loss (₹)</div>
                                    <div className="kpi-value">{formatCompactCurrency(kpis.surgery_audit_loss)}</div>
                                    <div className="kpi-desc"><span>🏥</span> HIS-scheduler gap</div>
                                </div>
                            </section>
                        )}

                {/* Interactive Message Feed */}
                <section className="chat-feed" style={{ display: compareMode && messages[bot].length > 0 ? 'flex' : undefined, flexDirection: compareMode && messages[bot].length > 0 ? 'row' : undefined, gap: compareMode && messages[bot].length > 0 ? '20px' : undefined, alignItems: compareMode && messages[bot].length > 0 ? 'stretch' : undefined }}>
                    {messages[bot].length === 0 ? (
                        <div className="empty-state-container" style={{ width: '100%' }}>
                            <EmptyIllustration />
                            <h3 className="empty-state-title">Consultation Workspace</h3>
                            <p className="empty-state-subtitle">
                                Initiate analytical audits of billing logs or surgery registry entries. Choose one of our recommended queries below to start.
                            </p>
                            <div className="empty-state-grid">
                                {emptyQueries.map((item, idx) => (
                                    <div 
                                        key={idx} 
                                        className="example-query-card"
                                        onClick={() => handleSend(item.q)}
                                    >
                                        <div style={{ fontWeight: '600', color: 'var(--accent)', marginBottom: '4px' }}>{item.title}</div>
                                        <div>{item.q}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : compareMode ? (
                        <>
                            {/* Period A Pane */}
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', borderRight: '1px solid var(--border)', paddingRight: '20px', overflowY: 'auto' }}>
                                <div style={{ fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--accent)', borderBottom: '1px solid var(--border)', paddingBottom: '6px', marginBottom: '8px' }}>
                                    Period A: {filters.period === 'custom' ? `${filters.start} to ${filters.end}` : filters.period === 'all' ? 'All Records' : filters.period}
                                </div>
                                {messages[bot].map((msg, idx) => renderMessageBubble(msg, idx, 'A'))}
                            </div>
                            {/* Period B Pane */}
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                                <div style={{ fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--warning)', borderBottom: '1px solid var(--border)', paddingBottom: '6px', marginBottom: '8px' }}>
                                    Period B: {filtersB.period === 'custom' ? `${filtersB.start} to ${filtersB.end}` : filtersB.period === 'all' ? 'All Records' : filtersB.period}
                                </div>
                                {messages[bot].map((msg, idx) => renderMessageBubble(msg, idx, 'B'))}
                            </div>
                        </>
                    ) : (
                        messages[bot].map((msg, idx) => renderMessageBubble(msg, idx, 'single'))
                    )}
                </section>

                     {messages[bot].length > 0 && 
                      !isTyping && 
                      !messages[bot][messages[bot].length - 1].streaming && 
                      followUpSuggestions.length > 0 && (
                         <div className="follow-up-suggestions-container">
                             {followUpSuggestions.map((item, idx) => (
                                 <button 
                                     key={idx} 
                                     className="follow-up-chip"
                                     onClick={() => handleSend(item)}
                                 >
                                     {item}
                                 </button>
                             ))}
                         </div>
                     )}
                     
                     {isTyping && <SkeletonLoader />}
                     <div ref={chatFeedEndRef} />
                </section>

                {/* Input Workspace & Suggestions */}
                <section className="interaction-container">
                    {showSuggestions && suggestions.length > 0 && (
                        <div className="autocomplete-popup">
                            {suggestions.map((s, i) => (
                                <div 
                                    key={i} 
                                    className="autocomplete-row"
                                    onClick={() => handleSelectSuggestion(s)}
                                >
                                    <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" style={{ color: 'var(--accent)' }}><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                                    <span>{s}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="input-bar-wrapper">
                        <input 
                            type="text" 
                            className="chat-input"
                            placeholder={`Inquire about hospital ${bot === 'revenue' ? 'revenue leakage logs' : 'surgical audit discrepancies'}...`}
                            value={queryInput}
                            onChange={e => setQueryInput(e.target.value)}
                            onFocus={() => setShowSuggestions(true)}
                            onBlur={() => setTimeout(() => setShowSuggestions(false), 250)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && queryInput.trim()) {
                                    handleSend(queryInput);
                                }
                            }}
                        />
                        <button className="send-btn" onClick={() => handleSend(queryInput)} disabled={!queryInput.trim()}>
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                        </button>
                    </div>
                </section>
            </>)}
            </main>

            {/* COLUMN 3: RIGHT CONTEXT & FILTERS SIDEBAR */}
            {bot !== 'audit_logs' && (
                <aside className="right-sidebar">
                <h3 className="right-sidebar-title">Analytics & Context</h3>

                {/* COMPARE MODE TOGGLE */}
                <div className="filter-group" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '16px', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
                        <span className="filter-label" style={{ margin: 0 }}>Compare Mode</span>
                        <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', position: 'relative' }}>
                            <input 
                                type="checkbox" 
                                checked={compareMode} 
                                onChange={e => {
                                    setCompareMode(e.target.checked);
                                    if (e.target.checked && filtersB.period === 'all') {
                                        setFiltersB({ period: 'custom', start: '2024-04-01', end: '2024-06-30', location: filters.location });
                                    }
                                }} 
                                style={{ opacity: 0, position: 'absolute', width: 0, height: 0 }}
                            />
                            <div style={{
                                width: '38px',
                                height: '20px',
                                backgroundColor: compareMode ? 'var(--accent)' : 'var(--border)',
                                borderRadius: '10px',
                                transition: 'all 0.2s',
                                position: 'relative'
                            }}>
                                <div style={{
                                    width: '16px',
                                    height: '16px',
                                    backgroundColor: 'white',
                                    borderRadius: '50%',
                                    position: 'absolute',
                                    top: '2px',
                                    left: compareMode ? '20px' : '2px',
                                    transition: 'all 0.2s'
                                }}></div>
                            </div>
                        </label>
                    </div>
                </div>

                <div className="filter-group">
                    <div className="filter-label">{compareMode ? 'Period A Timeline' : 'Timeline Range'}</div>
                    <select 
                        className="filter-select"
                        value={filters.period}
                        onChange={e => setFilters({ ...filters, period: e.target.value })}
                    >
                        <option value="all">All Available Records</option>
                        <option value="1y">Past 1 Calendar Year</option>
                        <option value="1fy">Past Financial Year</option>
                        <option value="custom">Custom Calendar Date</option>
                    </select>

                    {filters.period === 'custom' && (
                        <div className="date-picker-row">
                            <input 
                                type="date" 
                                className="date-picker-input" 
                                value={filters.start}
                                onChange={e => setFilters({ ...filters, start: e.target.value })} 
                            />
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center' }}>to</div>
                            <input 
                                type="date" 
                                className="date-picker-input" 
                                value={filters.end}
                                onChange={e => setFilters({ ...filters, end: e.target.value })} 
                            />
                        </div>
                    )}
                </div>

                {compareMode && (
                    <div className="filter-group" style={{ borderTop: '1px dashed var(--border)', paddingTop: '16px' }}>
                        <div className="filter-label" style={{ color: 'var(--warning)' }}>Period B Timeline</div>
                        <select 
                            className="filter-select"
                            value={filtersB.period}
                            onChange={e => setFiltersB({ ...filtersB, period: e.target.value })}
                        >
                            <option value="all">All Available Records</option>
                            <option value="1y">Past 1 Calendar Year</option>
                            <option value="1fy">Past Financial Year</option>
                            <option value="custom">Custom Calendar Date</option>
                        </select>

                        {filtersB.period === 'custom' && (
                            <div className="date-picker-row">
                                <input 
                                    type="date" 
                                    className="date-picker-input" 
                                    value={filtersB.start}
                                    onChange={e => setFiltersB({ ...filtersB, start: e.target.value })} 
                                />
                                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center' }}>to</div>
                                <input 
                                    type="date" 
                                    className="date-picker-input" 
                                    value={filtersB.end}
                                    onChange={e => setFiltersB({ ...filtersB, end: e.target.value })} 
                                />
                            </div>
                        )}
                    </div>
                )}

                <div className="filter-group">
                    <div className="filter-label">Location In-Scope</div>
                    <select 
                        className="filter-select"
                        value={filters.location}
                        onChange={e => setFilters({ ...filters, location: e.target.value })}
                    >
                        <option value="">All Hospital Wards</option>
                        {locations.map((loc, idx) => (
                            <option key={idx} value={loc}>{loc}</option>
                        ))}
                    </select>
                </div>

                {/* Dropzone File Upload Ingestion */}
                <div 
                    className={`upload-dropzone ${dragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('file-upload-input').click()}
                >
                    <svg className="upload-icon" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                    </svg>
                    <span className="upload-text">Drag & drop raw reports here</span>
                    <span className="upload-subtext">Supports PDF, XLSX or XLS formats</span>
                    <input 
                        id="file-upload-input" 
                        type="file" 
                        className="hidden" 
                        style={{ display: 'none' }}
                        accept=".xlsx,.xls,.pdf" 
                        onChange={e => handleFileUpload(e.target.files[0])} 
                    />
                </div>

                {uploadProgress.state !== 'idle' && (
                    <div style={{ 
                        marginTop: '12px', 
                        padding: '10px', 
                        borderRadius: '8px', 
                        fontSize: '11px', 
                        textAlign: 'center',
                        fontWeight: '500',
                        backgroundColor: uploadProgress.state === 'loading' ? 'var(--accent-light)' : uploadProgress.state === 'success' ? 'rgba(158, 206, 106, 0.15)' : 'rgba(247, 118, 142, 0.15)',
                        color: uploadProgress.state === 'loading' ? 'var(--accent)' : uploadProgress.state === 'success' ? 'var(--success)' : 'var(--danger)',
                        border: '1px solid ' + (uploadProgress.state === 'loading' ? 'var(--accent)' : uploadProgress.state === 'success' ? 'var(--success)' : 'var(--danger)')
                    }}>
                        {uploadProgress.message}
                    </div>
                )}

                <div style={{ marginTop: '24px', backgroundColor: 'var(--background)', borderRadius: '12px', padding: '16px', border: '1px solid var(--border)' }}>
                    <div className="filter-label" style={{ marginBottom: '8px' }}>Database Health</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '4px 0' }}>
                        <span>Server Status</span>
                        <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>ONLINE</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '4px 0' }}>
                        <span>Database Source</span>
                        <span style={{ color: 'var(--accent)', fontWeight: '500' }}>SQLite</span>
                    </div>
                </div>
            </aside>
            )}

            {/* GLOBAL MODAL: ⌘K COMMAND PALETTE */}
            <CommandPalette 
                isOpen={commandBarOpen}
                onClose={() => setCommandBarOpen(false)}
                bot={bot}
                setBot={setBot}
                user={user}
                filters={filters}
                setFilters={setFilters}
                handleSend={handleSend}
                loadSession={loadSession}
                theme={theme}
                toggleTheme={toggleTheme}
                handleNewChat={handleNewChat}
                onLogout={handleLogout}
                messages={messages}
            />

            {/* HUMAN FEEDBACK CRITIQUE MODAL */}
            {feedbackModalOpen && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.65)',
                    backdropFilter: 'blur(4px)',
                    zIndex: 9999,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <div style={{
                        backgroundColor: 'var(--card-background)',
                        border: '1px solid var(--border)',
                        borderRadius: '16px',
                        padding: '24px',
                        width: '90%',
                        maxWidth: '450px',
                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
                        color: 'var(--text-primary)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
                                Report Response Quality Issue
                            </h3>
                            <button 
                                onClick={() => setFeedbackModalOpen(false)}
                                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '18px' }}
                            >
                                &times;
                            </button>
                        </div>
                        
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                            Your feedback helps tune the underlying semantic audit engines. What was wrong with the bot's response?
                        </p>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                            {['Wrong numbers', 'Missing data', 'Bad interpretation', 'Other'].map(type => (
                                <label 
                                    key={type} 
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px',
                                        padding: '10px 14px',
                                        borderRadius: '8px',
                                        border: '1px solid ' + (feedbackType === type ? 'var(--accent)' : 'var(--border)'),
                                        backgroundColor: feedbackType === type ? 'var(--accent-light)' : 'transparent',
                                        cursor: 'pointer',
                                        fontSize: '13px',
                                        fontWeight: feedbackType === type ? '500' : 'normal',
                                        color: feedbackType === type ? 'var(--accent)' : 'var(--text-primary)',
                                        position: 'relative'
                                    }}
                                >
                                    <input 
                                        type="radio" 
                                        name="feedbackType" 
                                        value={type} 
                                        checked={feedbackType === type}
                                        onChange={() => setFeedbackType(type)}
                                        style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
                                    />
                                    {type}
                                </label>
                            ))}
                        </div>
                        
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 'bold' }}>
                                Critique Comment (Optional)
                            </label>
                            <textarea 
                                value={feedbackComment}
                                onChange={e => setFeedbackComment(e.target.value)}
                                placeholder="Describe the discrepancy in detail..."
                                style={{
                                    width: '100%',
                                    minHeight: '80px',
                                    backgroundColor: 'var(--background)',
                                    border: '1px solid var(--border)',
                                    borderRadius: '8px',
                                    padding: '10px',
                                    color: 'var(--text-primary)',
                                    fontFamily: 'var(--font-body)',
                                    fontSize: '12px',
                                    outline: 'none',
                                    resize: 'vertical'
                                }}
                            />
                        </div>
                        
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button 
                                onClick={() => setFeedbackModalOpen(false)}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border)',
                                    backgroundColor: 'transparent',
                                    color: 'var(--text-secondary)',
                                    fontSize: '13px',
                                    cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button 
                                onClick={() => {
                                    if (feedbackMsg) {
                                        handleFeedbackSubmit(feedbackMsg.msg, feedbackMsg.idx, feedbackType, feedbackComment);
                                    }
                                    setFeedbackModalOpen(false);
                                }}
                                style={{
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    backgroundColor: 'var(--accent)',
                                    color: 'white',
                                    fontSize: '13px',
                                    fontWeight: '500',
                                    cursor: 'pointer'
                                }}
                            >
                                Submit Critique
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* RIGHT SIDE DRAWER FOR DETAILED TRANSACTION BREAKDOWNS */}
            {drawerOpen && (
                <div 
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity flex justify-end"
                    onClick={() => setDrawerOpen(false)}
                >
                    <div 
                        className="w-full max-w-2xl h-full bg-[var(--card-background)] border-l border-[var(--border)] shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out text-[var(--text-primary)]"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Drawer Header */}
                        <div className="p-6 border-b border-[var(--border)] flex justify-between items-center bg-[var(--card-background)]">
                            <div>
                                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">
                                    Breakdown Audit Details
                                </span>
                                <h3 className="text-2xl font-bold font-heading mt-1 text-[var(--text-primary)]">
                                    {clickedBarName || 'Transaction breakdown'}
                                </h3>
                                <p className="text-xs text-[var(--text-secondary)] mt-1">
                                    Analyzing leakage from: "{clickedBarQuery}"
                                </p>
                            </div>
                            <button 
                                className="p-2 rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all cursor-pointer"
                                onClick={() => setDrawerOpen(false)}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Summary Info Cards */}
                        {drawerData && drawerData.summary && (
                            <div className="px-6 py-4 bg-[var(--background)] border-b border-[var(--border)] grid grid-cols-3 gap-4">
                                <div className="p-3 bg-[var(--card-background)] border border-[var(--border)] rounded-xl">
                                    <div className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">Category</div>
                                    <div className="text-sm font-semibold capitalize text-[var(--text-primary)] mt-1">
                                        {drawerData.summary.category || 'Details'}
                                    </div>
                                </div>
                                <div className="p-3 bg-[var(--card-background)] border border-[var(--border)] rounded-xl">
                                    <div className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">Total Leakage</div>
                                    <div className="text-lg font-bold text-[var(--danger)] mt-0.5">
                                        ₹{drawerData.summary.total_leakage.toLocaleString('en-IN')}
                                    </div>
                                </div>
                                <div className="p-3 bg-[var(--card-background)] border border-[var(--border)] rounded-xl">
                                    <div className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">Occurrences</div>
                                    <div className="text-lg font-bold text-[var(--accent)] mt-0.5">
                                        {drawerData.summary.count} cases
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Tabs Navigation */}
                        <div className="px-6 border-b border-[var(--border)] flex justify-between items-center bg-[var(--card-background)]">
                            <div className="flex gap-4">
                                {[
                                    { id: 'transactions', label: 'Transactions' },
                                    { id: 'staff', label: bot === 'revenue' ? 'By Staff' : 'By Surgeon' },
                                    { id: 'trend', label: 'Monthly Trend' }
                                ].map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setDrawerTab(tab.id)}
                                        className={`py-4 px-2 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
                                            drawerTab === tab.id
                                                ? 'border-[var(--accent)] text-[var(--accent)] font-bold'
                                                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                                        }`}
                                    >
                                        {tab.label}
                                    </button>
                                ))}
                            </div>
                            
                            {/* Action Buttons */}
                            <div className="flex gap-2 py-2">
                                <button
                                    onClick={() => {
                                        if (drawerData && drawerData.transactions) {
                                            exportToCsv(drawerData.transactions, `leakage_${clickedBarName.replace(/\s+/g, '_')}.csv`);
                                            fetch(`${API_BASE}/export/excel?username=${encodeURIComponent(user.username)}`, { method: 'POST' }).catch(console.error);
                                        }
                                    }}
                                    disabled={!drawerData || !drawerData.transactions || drawerData.transactions.length === 0}
                                    className="py-1.5 px-3 text-xs font-semibold rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                >
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                                    </svg>
                                    CSV
                                </button>
                                <button
                                    onClick={handleAskAboutThis}
                                    className="py-1.5 px-3 text-xs font-semibold rounded-lg bg-[var(--background)] border border-[var(--border)] text-[var(--text-primary)] hover:border-[var(--accent)] hover:text-[var(--accent)] flex items-center gap-1.5 cursor-pointer transition-all"
                                >
                                    <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                        <circle cx="11" cy="11" r="8" />
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35" />
                                    </svg>
                                    Ask
                                </button>
                            </div>
                        </div>

                        {/* Content Area */}
                        <div className="flex-1 overflow-y-auto p-6 bg-[var(--background)]">
                            {drawerLoading ? (
                                <div className="flex flex-col items-center justify-center h-64 gap-3">
                                    <div className="w-8 h-8 rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] animate-spin"></div>
                                    <span className="text-xs text-[var(--text-secondary)] italic">Analyzing raw transactions...</span>
                                </div>
                            ) : !drawerData || (drawerTab === 'transactions' && drawerData.transactions.length === 0) ? (
                                <div className="flex flex-col items-center justify-center h-64 text-[var(--text-muted)] italic text-sm">
                                    No records found for "{clickedBarName}"
                                </div>
                            ) : (
                                <div>
                                    {/* TAB 1: TRANSACTIONS LIST */}
                                    {drawerTab === 'transactions' && (
                                        <div className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card-background)]">
                                            <table className="w-full text-left border-collapse text-xs">
                                                <thead>
                                                    <tr className="bg-[var(--background)] border-b border-[var(--border)] text-[var(--text-muted)] font-semibold uppercase tracking-wider">
                                                        <th className="p-3.5">Date</th>
                                                        <th className="p-3.5">Patient ID</th>
                                                        <th className="p-3.5">Service/Procedure</th>
                                                        <th className="p-3.5 text-right">Amount</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-[var(--border)] text-[var(--text-primary)]">
                                                    {drawerData.transactions.map((tx, idx) => (
                                                        <tr key={idx} className="hover:bg-[var(--accent-light)] transition-colors">
                                                            <td className="p-3.5 whitespace-nowrap">{tx.date}</td>
                                                            <td className="p-3.5 font-mono">{tx.patient_id}</td>
                                                            <td className="p-3.5 font-medium">{tx.service_name}</td>
                                                            <td className="p-3.5 text-right font-semibold text-[var(--danger)]">
                                                                ₹{tx.leakage_amount.toLocaleString('en-IN')}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}

                                    {/* TAB 2: BY STAFF / SURGEON */}
                                    {drawerTab === 'staff' && (
                                        <div className="flex flex-col gap-4">
                                            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
                                                Leakage Distribution by Medical Staff
                                            </h4>
                                            {drawerData.by_staff.map((staff, idx) => {
                                                const totalSum = drawerData.summary.total_leakage || 1;
                                                const percentage = Math.round((staff.leakage_amount / totalSum) * 100);
                                                return (
                                                    <div key={idx} className="p-4 bg-[var(--card-background)] border border-[var(--border)] rounded-xl flex flex-col gap-2">
                                                        <div className="flex justify-between items-center text-xs">
                                                            <span className="font-semibold text-[var(--text-primary)]">
                                                                {staff.staff_name || 'Unknown Staff'}
                                                            </span>
                                                            <span className="font-bold text-[var(--danger)]">
                                                                ₹{staff.leakage_amount.toLocaleString('en-IN')} ({percentage}%)
                                                            </span>
                                                        </div>
                                                        <div className="w-full bg-[var(--background)] h-2 rounded-full overflow-hidden border border-[var(--border)]">
                                                            <div 
                                                                className="bg-[var(--accent)] h-full rounded-full transition-all duration-500"
                                                                style={{ width: `${percentage}%` }}
                                                            ></div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                            {drawerData.by_staff.length === 0 && (
                                                <div className="text-center italic text-xs text-[var(--text-muted)] py-8">
                                                    No staff breakdowns recorded
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* TAB 3: MONTHLY TREND */}
                                    {drawerTab === 'trend' && (
                                        <div className="flex flex-col gap-3">
                                            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
                                                Chronological Trend Breakdown
                                            </h4>
                                            <div className="relative border-l border-[var(--border)] ml-3 pl-6 flex flex-col gap-6">
                                                {drawerData.monthly_trend.map((trend, idx) => (
                                                    <div key={idx} className="relative">
                                                        {/* Circle indicator */}
                                                        <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-[var(--accent)] border-2 border-[var(--card-background)]"></div>
                                                        <div className="p-4 bg-[var(--card-background)] border border-[var(--border)] rounded-xl flex justify-between items-center text-xs">
                                                            <span className="font-semibold text-[var(--text-secondary)]">
                                                                {trend.month}
                                                            </span>
                                                            <span className="font-bold text-[var(--danger)]">
                                                                ₹{trend.leakage_amount.toLocaleString('en-IN')}
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            {drawerData.monthly_trend.length === 0 && (
                                                <div className="text-center italic text-xs text-[var(--text-muted)] py-8">
                                                    No trend history found
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
