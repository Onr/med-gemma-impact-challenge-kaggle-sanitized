import React, { useState, useRef, useEffect } from 'react';
import { AppState, Phase, Reference, AppraisalPoint, ApplyPoint, AssessPoint, PicoData } from '../types';

interface InfoPanelProps {
    state: AppState;
    onChangePhase: (p: Phase) => void;
    onChipClick: (text: string) => void;
    onPicoEdit?: (field: keyof PicoData, value: string) => void;
}

// Quality levels for PICO field confidence indicators
type FieldQuality = 'GOOD' | 'MINIMAL' | 'EMPTY';

const getFieldQuality = (value: string): FieldQuality => {
    if (!value || value.trim() === '') return 'EMPTY';
    const normalized = value.trim().toLowerCase();
    // Check for placeholder values
    if (['unknown', 'tbd', 'n/a', 'na', '-', 'none'].includes(normalized)) return 'EMPTY';
    const wordCount = value.trim().split(/\s+/).length;
    if (wordCount >= 10) return 'GOOD';
    return 'MINIMAL';
};

const qualityColors: Record<FieldQuality, { bg: string; dot: string; label: string }> = {
    GOOD: { bg: 'bg-emerald-500/20', dot: 'bg-emerald-500', label: 'Complete' },
    MINIMAL: { bg: 'bg-amber-500/20', dot: 'bg-amber-500', label: 'Minimal' },
    EMPTY: { bg: 'bg-rose-500/20', dot: 'bg-rose-500', label: 'Missing' }
};

const InfoPanel: React.FC<InfoPanelProps> = ({ state, onChangePhase, onChipClick, onPicoEdit }) => {
    const { currentPhase, pico, references, appraisals, applyPoints, assessPoints } = state;
    const [editingField, setEditingField] = useState<keyof PicoData | null>(null);
    const [editValue, setEditValue] = useState('');
    const picoSectionRef = useRef<HTMLDivElement>(null);

    // Scroll to PICO section when entering ASK phase
    useEffect(() => {
        if (currentPhase === Phase.ASK && picoSectionRef.current) {
            picoSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [currentPhase]);

    // Get guidance for completeness tooltip
    const getCompletenessGuidance = () => {
        const fields: { name: string; key: keyof PicoData; optional?: boolean }[] = [
            { name: 'Patient/Problem', key: 'patient' },
            { name: 'Intervention', key: 'intervention' },
            { name: 'Comparison', key: 'comparison', optional: true },
            { name: 'Outcome', key: 'outcome' }
        ];
        const missing = fields.filter(f => getFieldQuality(pico[f.key] as string) === 'EMPTY');
        const minimal = fields.filter(f => getFieldQuality(pico[f.key] as string) === 'MINIMAL');

        let guidance = `${pico.completeness}% complete`;
        if (missing.length > 0) {
            const required = missing.filter(f => !f.optional);
            if (required.length > 0) guidance += `\nFill: ${required.map(f => f.name).join(', ')}`;
        }
        if (minimal.length > 0) {
            guidance += `\nExpand: ${minimal.map(f => f.name).join(', ')}`;
        }
        if (missing.some(f => f.optional)) guidance += '\n(Comparison is optional)';
        return guidance;
    };

    const handleStartEdit = (field: keyof PicoData, currentValue: string) => {
        if (!onPicoEdit) return;
        setEditingField(field);
        setEditValue(currentValue);
    };

    const handleSaveEdit = () => {
        if (editingField && onPicoEdit && editingField !== 'completeness') {
            onPicoEdit(editingField, editValue);
        }
        setEditingField(null);
        setEditValue('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSaveEdit();
        } else if (e.key === 'Escape') {
            setEditingField(null);
            setEditValue('');
        }
    };

    const renderPicoChip = (label: string, value: string, colorClass: string, field: keyof PicoData) => {
        const isEditing = editingField === field;
        const canEdit = onPicoEdit && field !== 'completeness';
        const quality = getFieldQuality(value);
        const qColors = qualityColors[quality];

        return (
            <div
                className={`rounded-lg p-3 border relative group transition-colors h-full ${canEdit ? 'cursor-pointer' : ''}`}
                style={{ 
                    backgroundColor: 'var(--color-bg-secondary)', 
                    borderColor: isEditing ? 'var(--color-accent)' : 'var(--color-border)' 
                }}
                onClick={() => !isEditing && canEdit && handleStartEdit(field, value)}
            >
                <div className={`text-[10px] uppercase tracking-wider font-bold mb-1 ${colorClass} flex items-center gap-1.5`}>
                    {/* Quality indicator dot */}
                    <span
                        className={`w-2 h-2 rounded-full ${qColors.dot} flex-shrink-0`}
                        title={qColors.label}
                    />
                    {label}
                    {canEdit && !isEditing && (
                        <span className="material-symbols-outlined text-[10px] opacity-0 group-hover:opacity-50">edit</span>
                    )}
                </div>
                {isEditing ? (
                    <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={handleSaveEdit}
                        onKeyDown={handleKeyDown}
                        autoFocus
                        className="w-full bg-transparent border-b border-sky-500 px-0 py-1 text-sm focus:outline-none"
                        style={{ color: 'var(--color-text-primary)' }}
                        onClick={(e) => e.stopPropagation()}
                    />
                ) : (
                    <div className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
                        {value || <span className="italic opacity-40">Click to edit...</span>}
                    </div>
                )}
            </div>
        );
    };

    const getVerdictColor = (verdict: AppraisalPoint['verdict']) => {
        switch (verdict) {
            case 'Positive': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
            case 'Negative': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
            case 'Neutral': return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
            default: return 'bg-slate-700/10 text-slate-500';
        }
    };

    const formatTime = (ts?: number) => {
        if (!ts) return '';
        return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // Common grid class for all phases
    const gridClass = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4";

    return (
        <div className="bg-transparent flex flex-col h-full w-full theme-transition">
            {/* Tabs */}
            <div className="flex backdrop-blur-md" style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
                {[Phase.ASK, Phase.ACQUIRE, Phase.APPRAISE, Phase.APPLY, Phase.ASSESS].map((p) => (
                    <button
                        key={p}
                        onClick={() => onChangePhase(p)}
                        className={`px-6 py-2.5 text-xs font-medium transition-colors border-b-2 whitespace-nowrap ${currentPhase === p
                            ? 'border-sky-500'
                            : 'border-transparent opacity-60 hover:opacity-100'
                            }`}
                        style={{ 
                            color: currentPhase === p ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                            backgroundColor: currentPhase === p ? 'var(--color-bg-tertiary)' : 'transparent'
                        }}
                    >
                        {p}
                    </button>
                ))}
            </div>

            <div className="p-4 md:p-6 overflow-y-auto flex-1 scrollbar-hide">

                {/* ASK Content */}
                {currentPhase === Phase.ASK && (
                    <div ref={picoSectionRef} className="space-y-4 animate-fade-in h-full flex flex-col">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="text-sm font-semibold text-sky-500 uppercase tracking-wider">Clinical Question (PICO)</h3>
                            <div
                                className="flex items-center gap-3 w-64 cursor-help"
                                title={getCompletenessGuidance()}
                            >
                                <div className="text-xs opacity-60" style={{ color: 'var(--color-text-secondary)' }}>Completeness: {pico.completeness}%</div>
                                <div className="h-1.5 flex-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                                    <div
                                        className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-all duration-700"
                                        style={{ width: `${pico.completeness}%` }}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className={gridClass}>
                            {renderPicoChip('Patient / Problem', pico.patient, 'text-blue-500', 'patient')}
                            {renderPicoChip('Intervention', pico.intervention, 'text-emerald-500', 'intervention')}
                            {renderPicoChip('Comparison', pico.comparison, 'text-amber-500', 'comparison')}
                            {renderPicoChip('Outcome', pico.outcome, 'text-rose-500', 'outcome')}
                        </div>
                    </div>
                )}

                {/* ACQUIRE Content */}
                {currentPhase === Phase.ACQUIRE && (
                    <div className="space-y-4 animate-fade-in">
                        <h3 className="text-sm font-semibold text-emerald-500 uppercase tracking-wider mb-2">Evidence Library</h3>
                        {references.length === 0 ? (
                            <div className="text-sm italic text-center py-8 border border-dashed rounded-xl" style={{ color: 'var(--color-text-muted)', borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
                                No references collected yet. Ask the Copilot to search for evidence.
                            </div>
                        ) : (
                            <div className={gridClass}>
                                {references.map(ref => (
                                    <div
                                        key={ref.id}
                                        className="p-3 rounded-lg border transition-all group h-full flex flex-col"
                                        style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-[10px] bg-emerald-500/20 text-emerald-500 px-1.5 py-0.5 rounded font-bold">{ref.type}</span>
                                            <div className="text-[10px] opacity-60 flex gap-2" style={{ color: 'var(--color-text-secondary)' }}>
                                                <span>{ref.year}</span>
                                            </div>
                                        </div>
                                        <div
                                            onClick={() => onChipClick(`Re: Study "${ref.title}" (${ref.year}) - `)}
                                            className="font-medium text-sm mb-auto group-hover:text-emerald-500 transition-colors line-clamp-2 cursor-pointer"
                                            style={{ color: 'var(--color-text-primary)' }}
                                        >
                                            {ref.title}
                                        </div>
                                        <div className="text-xs mt-2 opacity-60" style={{ color: 'var(--color-text-secondary)' }}>{ref.source}</div>
                                        {ref.url && (
                                            <a
                                                href={ref.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                onClick={(e) => e.stopPropagation()}
                                                className="text-xs text-emerald-500 hover:underline mt-2 flex items-center gap-1"
                                            >
                                                <span>View on PubMed</span>
                                                <span className="material-symbols-outlined text-xs">open_in_new</span>
                                            </a>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* APPRAISE Content */}
                {currentPhase === Phase.APPRAISE && (
                    <div className="space-y-4 animate-fade-in">
                        <h3 className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-2">Critical Appraisal</h3>
                        {appraisals.length === 0 ? (
                            <div className="text-sm italic text-center py-8 border border-dashed rounded-xl" style={{ color: 'var(--color-text-muted)', borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
                                No appraisal points yet. Discuss specific studies to evaluate them.
                            </div>
                        ) : (
                            <div className={gridClass}>
                                {appraisals.map((item) => (
                                    <div
                                        key={item.id}
                                        onClick={() => onChipClick(`Re: Appraisal point "${item.title}" - `)}
                                        className={`p-3 rounded-lg border ${getVerdictColor(item.verdict)} cursor-pointer hover:bg-opacity-20 transition-all h-full flex flex-col`}
                                    >
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="font-bold text-xs uppercase tracking-wide truncate pr-2">{item.title}</span>
                                            <div className="flex items-center gap-1 shrink-0">
                                                {item.verdict === 'Positive' && <span className="material-symbols-outlined text-sm">check_circle</span>}
                                                {item.verdict === 'Negative' && <span className="material-symbols-outlined text-sm">warning</span>}
                                                {item.verdict === 'Neutral' && <span className="material-symbols-outlined text-sm">remove_circle</span>}
                                            </div>
                                        </div>
                                        <div className="text-sm opacity-90 leading-tight">
                                            {item.description}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* APPLY Content */}
                {currentPhase === Phase.APPLY && (
                    <div className="space-y-4 animate-fade-in">
                        <h3 className="text-sm font-semibold text-purple-500 uppercase tracking-wider mb-2">Clinical Actions</h3>
                        {applyPoints.length === 0 ? (
                            <div className="text-sm font-medium text-center py-8 border border-dashed rounded-xl" style={{ color: 'var(--color-text-secondary)', borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
                                No action items yet. Ask to synthesize evidence into a plan.
                            </div>
                        ) : (
                            <div className={gridClass}>
                                {applyPoints.map((item) => (
                                    <div
                                        key={item.id}
                                        onClick={() => onChipClick(`Re: Action "${item.action}" - `)}
                                        className="p-3 rounded-lg border hover:border-purple-500/50 cursor-pointer transition-all h-full flex flex-col"
                                        style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-[10px] bg-purple-500/20 text-purple-500 px-1.5 py-0.5 rounded uppercase font-bold">Action</span>
                                        </div>
                                        <div className="font-medium text-sm mb-2" style={{ color: 'var(--color-text-primary)' }}>{item.action}</div>
                                        <div className="text-xs italic mt-auto opacity-60" style={{ color: 'var(--color-text-secondary)' }}>"{item.rationale}"</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ASSESS Content */}
                {currentPhase === Phase.ASSESS && (
                    <div className="space-y-4 animate-fade-in">
                        <h3 className="text-sm font-semibold text-rose-500 uppercase tracking-wider mb-2">Outcome Measures</h3>
                        {assessPoints.length === 0 ? (
                            <div className="text-sm italic text-center py-8 border border-dashed rounded-xl" style={{ color: 'var(--color-text-muted)', borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-secondary)' }}>
                                No outcome measures defined yet. Ask to define metrics for success.
                            </div>
                        ) : (
                            <div className={gridClass}>
                                {assessPoints.map((item) => (
                                    <div
                                        key={item.id}
                                        onClick={() => onChipClick(`Re: Metric "${item.metric}" - `)}
                                        className="p-3 rounded-lg border hover:border-rose-500/50 cursor-pointer transition-all h-full flex flex-col"
                                        style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-[10px] bg-rose-500/20 text-rose-500 px-1.5 py-0.5 rounded uppercase font-bold">Metric</span>
                                        </div>
                                        <div className="font-medium text-sm mb-2" style={{ color: 'var(--color-text-primary)' }}>{item.metric}</div>
                                        <div className="flex justify-between text-xs mt-auto border-t pt-2" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
                                            <span>Target: <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>{item.target}</span></span>
                                            <span>Freq: <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>{item.frequency}</span></span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

            </div>
        </div>
    );
};

export default InfoPanel;
