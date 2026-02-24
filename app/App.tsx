
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { AppState, Message, MessageImage, Phase, Role, ModelKey, Reference } from './types';
import RadialProgress from './components/RadialProgress';
import ChatPanel from './components/ChatPanel';
import InfoPanel from './components/InfoPanel';
import SettingsModal from './components/SettingsModal';
import ThemeToggle from './components/ThemeToggle';
import { sendMessageToMedGemma, MEDGEMMA_MODELS } from './services/medGemmaService';
import { searchPubMed, searchPubMedWithMeta, searchPubMedCustomTerms } from './services/pubmedService';

const App: React.FC = () => {
    const [state, setState] = useState<AppState>({
        currentPhase: Phase.ASK,
        userRole: Role.PHYSICIAN,
        patientContext: '',
        pico: { patient: '', intervention: '', comparison: '', outcome: '', completeness: 0 },
        references: [],
        appraisals: [],
        applyPoints: [],
        assessPoints: [],
        messages: [
            {
                id: 'init',
                role: 'model',
                content: "Hello. I am MedGemma, your EBP Copilot. I can help you structure your clinical question using PICO framework. You can also upload medical images (X-rays, dermoscopy, pathology) for analysis. Please describe your patient case.",
                timestamp: Date.now(),
                phase: Phase.ASK
            }
        ],
        isLoading: false,
        selectedModel: 'medgemma-4b-it', // Default to multimodal model
    });

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [draftInput, setDraftInput] = useState<string>('');
    const pubmedFetchedForPico = useRef<string>(''); // tracks which PICO we've already fetched for

    // Theme state with localStorage persistence
    const [isDarkTheme, setIsDarkTheme] = useState(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('medgemma-theme');
            // Default to dark if no preference saved
            return saved ? saved === 'dark' : true;
        }
        return true;
    });

    // Apply theme to document
    useEffect(() => {
        const root = document.documentElement;
        if (isDarkTheme) {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
        localStorage.setItem('medgemma-theme', isDarkTheme ? 'dark' : 'light');
    }, [isDarkTheme]);

    const toggleTheme = () => setIsDarkTheme(prev => !prev);

    // Fetch PubMed references with smart retry and AI-assisted refinement
    const fetchAndShowPubMed = useCallback(async (pico: typeof state.pico) => {
        if (pico.completeness < 50) return;
        const picoKey = `${pico.patient}|${pico.intervention}|${pico.outcome}`;
        if (pubmedFetchedForPico.current === picoKey) return;
        pubmedFetchedForPico.current = picoKey;

        try {
            console.log('[App] Fetching PubMed references for PICO:', pico);
            setState(prev => ({ ...prev, isLoading: true }));

            // Phase 1: Try all built-in search strategies
            const searchResult = await searchPubMedWithMeta(pico);

            if (searchResult.references.length > 0) {
                const refs = searchResult.references;
                const refLines = refs.map((r, i) =>
                    `**${i + 1}. ${r.title}**\n*${r.source}* (${r.year}) — ${r.type} | Relevance: ${r.relevance}${r.url ? `\n[View on PubMed](${r.url})` : ''}`
                ).join('\n\n');

                const refMsg: Message = {
                    id: `pubmed-${Date.now()}`,
                    role: 'model',
                    content: `📚 **PubMed Search Results** (${refs.length} articles found)\n\nBased on your PICO question, here are the most relevant studies:\n\n${refLines}\n\nYou can select a study to move to the **APPRAISE** phase for critical evaluation.`,
                    timestamp: Date.now(),
                    phase: Phase.ACQUIRE,
                    extractedData: {
                        type: 'REFERENCE_UPDATE',
                        data: refs.map(r => ({
                            id: r.id,
                            title: r.title,
                            source: r.source,
                            year: r.year,
                            type: r.type,
                            relevance: r.relevance,
                            url: r.url,
                        }))
                    }
                };

                setState(prev => ({
                    ...prev,
                    messages: [...prev.messages, refMsg],
                    references: [...prev.references, ...refs.filter(
                        newRef => !prev.references.some(existing => existing.id === newRef.id)
                    )],
                    isLoading: false
                }));
                return;
            }

            // Phase 2: Ask AI to suggest better search terms
            console.log('[App] All PubMed strategies returned 0 results, asking AI for refinement...');
            const refinementPrompt = `The PubMed search returned no results for this PICO:
Patient: ${pico.patient}
Intervention: ${pico.intervention}
Comparison: ${pico.comparison}
Outcome: ${pico.outcome}

Please suggest 3-5 alternative PubMed search terms that would find relevant evidence. Return ONLY a JSON array of search terms, like: ["stroke rehabilitation", "task-oriented training", "ADL independence"]`;

            let aiTerms: string[] = [];
            try {
                const aiResult = await sendMessageToMedGemma(
                    [],
                    { text: refinementPrompt },
                    state.userRole,
                    Phase.ACQUIRE,
                    '',
                    state.selectedModel
                );
                const jsonMatch = aiResult.text.match(/\[([^\]]+)\]/);
                if (jsonMatch) {
                    aiTerms = JSON.parse(`[${jsonMatch[1]}]`).filter((t: any) => typeof t === 'string');
                }
            } catch (e) { console.warn('[App] AI term refinement failed:', e); }

            // Phase 3: Retry with AI-suggested terms
            if (aiTerms.length > 0) {
                console.log('[App] Retrying PubMed with AI-suggested terms:', aiTerms);
                try {
                    const retryRefs = await searchPubMedCustomTerms(aiTerms);
                    if (retryRefs.length > 0) {
                        const refLines = retryRefs.map((r, i) =>
                            `**${i + 1}. ${r.title}**\n*${r.source}* (${r.year}) — ${r.type} | Relevance: ${r.relevance}${r.url ? `\n[View on PubMed](${r.url})` : ''}`
                        ).join('\n\n');

                        const refMsg: Message = {
                            id: `pubmed-retry-${Date.now()}`,
                            role: 'model',
                            content: `📚 **PubMed Search Results** (${retryRefs.length} articles found via refined search)\n\nI refined the search terms and found these studies:\n\n${refLines}\n\nYou can select a study to move to the **APPRAISE** phase for critical evaluation.`,
                            timestamp: Date.now(),
                            phase: Phase.ACQUIRE,
                            extractedData: {
                                type: 'REFERENCE_UPDATE',
                                data: retryRefs.map(r => ({
                                    id: r.id, title: r.title, source: r.source,
                                    year: r.year, type: r.type, relevance: r.relevance, url: r.url,
                                }))
                            }
                        };

                        setState(prev => ({
                            ...prev,
                            messages: [...prev.messages, refMsg],
                            references: [...prev.references, ...retryRefs.filter(
                                newRef => !prev.references.some(existing => existing.id === newRef.id)
                            )],
                            isLoading: false
                        }));
                        return;
                    }
                } catch (e) { console.warn('[App] AI-refined PubMed retry failed:', e); }
            }

            // Phase 4: All attempts failed — ask user to help refine
            const suggestedTermsText = aiTerms.length > 0
                ? `\n\nI tried these alternative terms: **${aiTerms.join(', ')}** — but still found no results.`
                : '';

            const helpMsg: Message = {
                id: `pubmed-help-${Date.now()}`,
                role: 'model',
                content: `📚 **PubMed Search** — I wasn't able to find articles matching your PICO terms after multiple search strategies.${suggestedTermsText}\n\n**Can you help refine the search?** Try:\n- Using simpler medical terms (e.g., "stroke" instead of "cerebrovascular accident")\n- Broadening the intervention description\n- Mentioning the core condition and treatment approach\n\nJust type your refined search terms or describe what you're looking for, and I'll search again.`,
                timestamp: Date.now(),
                phase: Phase.ACQUIRE,
            };
            // Allow re-searching with the same PICO by resetting the key
            pubmedFetchedForPico.current = '';
            setState(prev => ({ ...prev, messages: [...prev.messages, helpMsg], isLoading: false }));
        } catch (error) {
            console.error('[App] PubMed search failed:', error);
            pubmedFetchedForPico.current = ''; // Allow retry
            setState(prev => ({ ...prev, isLoading: false }));
        }
    }, []);

    // Updated to support images
    const handleSendMessage = async (text: string, images?: MessageImage[]) => {
        // Optimistic UI Update
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
            timestamp: Date.now(),
            phase: state.currentPhase,
            images: images // Include images in message for display
        };

        setState(prev => ({
            ...prev,
            messages: [...prev.messages, userMsg],
            isLoading: true
        }));

        // API Call with images support
        const { text: aiResponseText, extractedData } = await sendMessageToMedGemma(
            [...state.messages, userMsg], // Pass history including new message
            {
                text,
                images: images?.map(img => ({ mimeType: img.mimeType, data: img.data }))
            },
            state.userRole,
            state.currentPhase,
            state.patientContext,
            state.selectedModel
        );

        // Determine if phase changed
        let newPhase = state.currentPhase;
        if (extractedData && extractedData.type === 'PHASE_CHANGE') {
            const potentialPhase = extractedData.data as Phase;
            if (Object.values(Phase).includes(potentialPhase)) {
                newPhase = potentialPhase;
            }
        }

        // Compute effective PICO (in case this response includes a PICO_UPDATE)
        let effectivePico = state.pico;
        if (extractedData && extractedData.type === 'PICO_UPDATE') {
            effectivePico = { ...state.pico, ...extractedData.data };
        }

        const modelMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: 'model',
            content: aiResponseText,
            timestamp: Date.now(),
            extractedData,
            phase: newPhase // Associate message with the NEW phase if changed
        };

        setState(prev => {
            let newState = {
                ...prev,
                currentPhase: newPhase,
                messages: [...prev.messages, modelMsg],
                isLoading: false
            };

            // Handle State Updates from AI JSON
            if (extractedData) {
                const timestamp = Date.now();
                if (extractedData.type === 'PICO_UPDATE') {
                    newState.pico = { ...prev.pico, ...extractedData.data };
                } else if (extractedData.type === 'REFERENCE_UPDATE') {
                    const newRefs = extractedData.data.map((r: any, idx: number) => ({
                        ...r,
                        id: `ref-${timestamp}-${idx}`,
                        timestamp
                    }));
                    newState.references = [...prev.references, ...newRefs];
                } else if (extractedData.type === 'APPRAISAL_UPDATE') {
                    const newAppraisals = extractedData.data.map((a: any, idx: number) => ({
                        ...a,
                        id: `apr-${timestamp}-${idx}`,
                        timestamp
                    }));
                    newState.appraisals = [...prev.appraisals, ...newAppraisals];
                } else if (extractedData.type === 'APPLY_UPDATE') {
                    const newPoints = extractedData.data.map((a: any, idx: number) => ({
                        ...a,
                        id: `apl-${timestamp}-${idx}`,
                        timestamp
                    }));
                    newState.applyPoints = [...prev.applyPoints, ...newPoints];
                } else if (extractedData.type === 'ASSESS_UPDATE') {
                    const newPoints = extractedData.data.map((a: any, idx: number) => ({
                        ...a,
                        id: `ass-${timestamp}-${idx}`,
                        timestamp
                    }));
                    newState.assessPoints = [...prev.assessPoints, ...newPoints];
                }
            }

            return newState;
        });

        // Auto-fetch PubMed when entering or already in ACQUIRE phase
        if (newPhase === Phase.ACQUIRE && effectivePico.completeness >= 50) {
            fetchAndShowPubMed(effectivePico);
        }

        // If user sends a message while in ACQUIRE phase and no refs yet, treat it as refined search
        if (state.currentPhase === Phase.ACQUIRE && newPhase === Phase.ACQUIRE && state.references.length === 0) {
            // Reset the fetch key so the search can run again with updated PICO
            pubmedFetchedForPico.current = '';
            if (effectivePico.completeness >= 50) {
                fetchAndShowPubMed(effectivePico);
            }
        }
    };

    const handlePhaseChange = async (phase: Phase) => {
        setState(prev => ({ ...prev, currentPhase: phase }));

        // Auto-fetch PubMed refs when entering ACQUIRE phase
        if (phase === Phase.ACQUIRE && state.pico.completeness >= 50) {
            fetchAndShowPubMed(state.pico);
        }
    };

    const handleModelChange = (model: ModelKey) => {
        setState(prev => ({ ...prev, selectedModel: model }));
    };

    const handleSettingsSave = (role: Role, context: string, model?: ModelKey) => {
        setState(prev => ({
            ...prev,
            userRole: role,
            patientContext: context,
            ...(model && { selectedModel: model })
        }));
    };

    const handleChipClick = (text: string) => {
        setDraftInput(prev => prev ? `${prev} ${text}` : text);
    };

    // Handle manual PICO edits from InfoPanel
    const handlePicoEdit = (field: keyof typeof state.pico, value: string) => {
        if (field === 'completeness') return; // Don't allow manual completeness edits

        setState(prev => {
            const newPico = { ...prev.pico, [field]: value };
            // Recalculate completeness: 25 points per non-empty field
            const fields = ['patient', 'intervention', 'comparison', 'outcome'] as const;
            const filledCount = fields.filter(f => newPico[f].trim().length > 0).length;
            newPico.completeness = filledCount * 25;

            return { ...prev, pico: newPico };
        });
    };

    return (
        <div className="app-shell flex flex-col h-screen w-screen overflow-hidden font-sans theme-transition" style={{ color: 'var(--color-text-primary)' }}>
            {/* SVG Texture Layer */}
            <div className="absolute inset-0 pointer-events-none -z-30 opacity-40" aria-hidden="true">
                <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <pattern id="hex-grid" width="64" height="56" patternUnits="userSpaceOnUse" patternTransform="scale(1.2)">
                            <path
                                d="M16 2 L48 2 L62 28 L48 54 L16 54 L2 28 Z"
                                fill="none"
                                stroke="var(--color-border)"
                                strokeWidth="1"
                            />
                        </pattern>
                        <radialGradient id="texture-glow-a" cx="20%" cy="18%" r="60%">
                            <stop offset="0%" stopColor="var(--color-glow-1)" stopOpacity="0.55" />
                            <stop offset="100%" stopColor="var(--color-glow-1)" stopOpacity="0" />
                        </radialGradient>
                        <radialGradient id="texture-glow-b" cx="82%" cy="84%" r="55%">
                            <stop offset="0%" stopColor="var(--color-glow-2)" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="var(--color-glow-2)" stopOpacity="0" />
                        </radialGradient>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#hex-grid)" />
                    <rect width="100%" height="100%" fill="url(#texture-glow-a)" />
                    <rect width="100%" height="100%" fill="url(#texture-glow-b)" />
                </svg>
            </div>

            <div className="flex flex-1 overflow-hidden">

                <SettingsModal
                    isOpen={isSettingsOpen}
                    onClose={() => setIsSettingsOpen(false)}
                    currentRole={state.userRole}
                    currentPatientContext={state.patientContext}
                    onSave={handleSettingsSave}
                />

                {/* Main Content Area (Left of Chat) */}
                <div className="flex-1 flex flex-col relative min-w-0">

                    {/* Background Decorative Gradient */}
                    <div className="absolute inset-0 -z-20" style={{ background: 'var(--color-bg-primary)' }}></div>
                    <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none opacity-50">
                        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full blur-[100px]" style={{ backgroundColor: 'var(--color-glow-1)' }}></div>
                        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full blur-[100px]" style={{ backgroundColor: 'var(--color-glow-2)' }}></div>
                    </div>

                    {/* Branding Header */}
                    <div className="absolute top-6 left-6 z-30 flex items-center gap-4">
                        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                            <span className="w-2 h-8 bg-sky-500 rounded-full"></span>
                            MedGemma <span style={{ color: 'var(--color-text-muted)' }} className="font-light">EBP</span>
                        </h1>
                        <ThemeToggle isDark={isDarkTheme} onToggle={toggleTheme} />
                    </div>

                    {/* Top Half: Radial Visualization */}
                    <div className="flex-1 relative flex items-center justify-center min-h-0">
                        <div className="scale-[0.7] md:scale-[0.75] lg:scale-[0.85] xl:scale-95 transition-transform">
                            <RadialProgress
                                currentPhase={state.currentPhase}
                                onPhaseSelect={handlePhaseChange}
                                picoCompleteness={state.pico.completeness}
                                patientContext={state.patientContext}
                                userRole={state.userRole}
                                onCenterClick={() => setIsSettingsOpen(true)}
                            />
                        </div>
                    </div>

                    {/* Bottom Half: Info Panel */}
                    <div className="liquid-panel h-[45vh] min-h-[300px] z-10 flex flex-col" style={{ borderTop: '1px solid var(--color-border)' }}>
                        <InfoPanel
                            state={state}
                            onChangePhase={handlePhaseChange}
                            onChipClick={handleChipClick}
                            onPicoEdit={handlePicoEdit}
                        />
                    </div>
                </div>

                {/* Right Area: Chat (Wider) */}
                <div className="glass-panel liquid-panel w-[500px] lg:w-[600px] xl:w-[700px] h-full z-20 flex-shrink-0" style={{ borderLeft: '1px solid var(--color-border)' }}>
                    <ChatPanel
                        messages={state.messages}
                        currentPhase={state.currentPhase}
                        onSendMessage={handleSendMessage}
                        isLoading={state.isLoading}
                        draftInput={draftInput}
                        onDraftInputConsumed={() => setDraftInput('')}
                        selectedModel={state.selectedModel}
                        onModelChange={handleModelChange}
                    />
                </div>

            </div>
        </div>
    );
};

export default App;
