/**
 * PubMed E-utilities Service
 * Uses NCBI E-utilities API to search and fetch real medical literature
 * API Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
 */

import { Reference, PicoData } from '../types';

// --- Configuration ---
const EUTILS_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const MAX_RESULTS = 10;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// Rate limiting: NCBI allows 3 requests/second without API key
let lastRequestTime = 0;
const MIN_REQUEST_INTERVAL_MS = 350; // ~3 req/sec with buffer

// --- Types ---
interface CacheEntry {
    data: Reference[];
    timestamp: number;
}

interface PubMedArticle {
    pmid: string;
    title: string;
    source: string;
    pubDate: string;
    pubTypes: string[];
}

// --- Cache ---
const CACHE_KEY_PREFIX = 'pubmed_cache_';

function getCacheKey(query: string): string {
    // Simple hash for cache key
    let hash = 0;
    for (let i = 0; i < query.length; i++) {
        const char = query.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return `${CACHE_KEY_PREFIX}${hash}`;
}

function getFromCache(query: string): Reference[] | null {
    try {
        const key = getCacheKey(query);
        const stored = localStorage.getItem(key);
        if (!stored) return null;

        const entry: CacheEntry = JSON.parse(stored);
        if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
            localStorage.removeItem(key);
            return null;
        }
        return entry.data;
    } catch {
        return null;
    }
}

function saveToCache(query: string, data: Reference[]): void {
    try {
        const key = getCacheKey(query);
        const entry: CacheEntry = { data, timestamp: Date.now() };
        localStorage.setItem(key, JSON.stringify(entry));
    } catch {
        // Cache storage might be full, ignore
    }
}

// --- Rate Limiting ---
async function waitForRateLimit(): Promise<void> {
    const now = Date.now();
    const elapsed = now - lastRequestTime;
    if (elapsed < MIN_REQUEST_INTERVAL_MS) {
        await new Promise(resolve => setTimeout(resolve, MIN_REQUEST_INTERVAL_MS - elapsed));
    }
    lastRequestTime = Date.now();
}

// --- PICO to Query Conversion ---

// Words that don't add search value
const STOP_WORDS = new Set([
    'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'and', 'or', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'by', 'from', 'that', 'this', 'than', 'not', 'no', 'but', 'if',
    'its', 'his', 'her', 'their', 'our', 'my', 'your', 'who', 'whom', 'which', 'what',
    'specifically', 'especially', 'particularly', 'mainly', 'primarily',
    'focusing', 'including', 'such', 'based', 'using', 'also', 'both',
    'about', 'more', 'most', 'less', 'fewer', 'greater', 'lower',
    'would', 'could', 'should', 'may', 'might', 'can', 'need', 'needs',
    'specific', 'general', 'overall', 'standard', 'combined',
    'phase', 'stage', 'level', 'type', 'form', 'resulting', 'leading',
    'without', 'between', 'through', 'among', 'across', 'currently',
    'well', 'due', 'during', 'after', 'before', 'over', 'under',
    // Demographics — not useful for PubMed search
    'male', 'female', 'old', 'year', 'years', 'weeks', 'week', 'months', 'month',
    'patient', 'patients', 'adults', 'adult', 'elderly', 'aged',
    'year-old', 'living', 'lives', 'independently',
    'improved', 'reduced', 'decreased', 'increased', 'safe', 'safely',
    'structured', 'focused', 'short', 'simple',
]);

/**
 * Known medical compound phrases that should stay together.
 * Ordered longest-first so greedy matching picks the best.
 */
const MEDICAL_PHRASES = [
    'task-oriented training', 'task oriented training',
    'constraint-induced movement therapy', 'constraint induced movement therapy',
    'activities of daily living', 'occupational therapy',
    'upper extremity', 'lower extremity',
    'systematic review', 'randomized controlled trial',
    'ischemic stroke', 'hemorrhagic stroke', 'cerebrovascular accident',
    'range of motion', 'motor recovery', 'functional independence',
    'caregiver coaching', 'caregiver training', 'caregiver education',
    'home-based rehabilitation', 'home based rehabilitation',
    'cognitive rehabilitation', 'neurological rehabilitation',
    'spinal cord injury', 'traumatic brain injury',
    'quality of life', 'patient satisfaction',
    'meal preparation', 'shower transfer', 'stair negotiation',
    'fine motor', 'gross motor',
    'physical therapy', 'speech therapy',
    'left-sided weakness', 'right-sided weakness', 'hemiparesis', 'hemiplegia',
    'subacute stroke', 'acute stroke', 'chronic stroke',
    'adl training', 'adl independence', 'adl performance',
    'graded practice', 'repetitive practice',
];

/**
 * Extract significant medical keywords/phrases from free-text PICO elements.
 * First tries to extract known medical phrases, then falls back to individual keywords.
 */
export function extractKeywords(text: string, max = 4): string[] {
    if (!text) return [];
    const lower = text.toLowerCase();
    const results: string[] = [];

    // First pass: extract known medical phrases
    for (const phrase of MEDICAL_PHRASES) {
        if (lower.includes(phrase) && results.length < max) {
            results.push(phrase);
        }
    }

    // Second pass: extract remaining significant individual words
    const cleaned = text.replace(/\([^)]*\)/g, ' ').replace(/[^\w\s-]/g, ' ');
    const words = cleaned
        .split(/\s+/)
        .map(w => w.toLowerCase().replace(/^-|-$/g, ''))
        .filter(w => w.length > 2 && !STOP_WORDS.has(w))
        // Skip words already part of an extracted phrase
        .filter(w => !results.some(r => r.includes(w)));

    for (const w of words) {
        if (results.length >= max) break;
        results.push(w);
    }

    return results;
}

/**
 * Converts PICO framework elements into an optimized PubMed search query.
 * Uses medical phrases (OR-joined within each PICO element) for better recall.
 */
export function picoToSearchQuery(pico: PicoData): string {
    const coreParts: string[] = [];  // Required: P and I
    const optionalParts: string[] = [];  // Optional: O (don't AND, too restrictive)

    if (pico.patient) {
        const words = extractKeywords(pico.patient, 4);
        if (words.length > 0) {
            coreParts.push(`(${words.map(w => `"${w}"[tiab]`).join(' OR ')})`);
        }
    }

    if (pico.intervention) {
        const words = extractKeywords(pico.intervention, 4);
        if (words.length > 0) {
            coreParts.push(`(${words.map(w => `"${w}"[tiab]`).join(' OR ')})`);
        }
    }

    // Outcome terms are optional (used only if we have few core terms)
    if (pico.outcome) {
        const words = extractKeywords(pico.outcome, 3);
        if (words.length > 0) {
            optionalParts.push(`(${words.map(w => `"${w}"[tiab]`).join(' OR ')})`);
        }
    }

    // Build query: always require P AND I; only add O if both P and I are present
    let query = coreParts.join(' AND ');
    // Only add outcome if we have at least 2 core parts (P+I) to avoid over-narrowing
    if (coreParts.length >= 2 && optionalParts.length > 0) {
        // Add outcome as optional boost — wrapped in OR with the core query
        query = `(${query}) AND (${optionalParts.join(' OR ')})`;
    }

    query += ' AND (randomized controlled trial[pt] OR meta-analysis[pt] OR systematic review[pt] OR clinical trial[pt] OR guideline[pt] OR review[pt])';

    const tenYearsAgo = new Date().getFullYear() - 10;
    query += ` AND ${tenYearsAgo}:3000[dp]`;

    return query;
}

// --- PubMed API Functions ---

/**
 * Search PubMed for articles matching the query
 * Returns list of PMIDs
 */
async function esearch(query: string): Promise<string[]> {
    await waitForRateLimit();

    const params = new URLSearchParams({
        db: 'pubmed',
        term: query,
        retmax: MAX_RESULTS.toString(),
        retmode: 'json',
        sort: 'relevance'
    });

    const response = await fetch(`${EUTILS_BASE}/esearch.fcgi?${params}`);
    if (!response.ok) {
        throw new Error(`PubMed search failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data.esearchresult?.idlist || [];
}

/**
 * Fetch article details for given PMIDs
 * Returns parsed article information
 */
async function efetch(pmids: string[]): Promise<PubMedArticle[]> {
    if (pmids.length === 0) return [];

    await waitForRateLimit();

    const params = new URLSearchParams({
        db: 'pubmed',
        id: pmids.join(','),
        retmode: 'xml',
        rettype: 'abstract'
    });

    const response = await fetch(`${EUTILS_BASE}/efetch.fcgi?${params}`);
    if (!response.ok) {
        throw new Error(`PubMed fetch failed: ${response.statusText}`);
    }

    const xmlText = await response.text();
    return parseXmlResponse(xmlText);
}

/**
 * Parse PubMed XML response into structured articles
 */
function parseXmlResponse(xmlText: string): PubMedArticle[] {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlText, 'text/xml');
    const articles: PubMedArticle[] = [];

    const articleNodes = doc.querySelectorAll('PubmedArticle');
    articleNodes.forEach(node => {
        const pmid = node.querySelector('PMID')?.textContent || '';
        const title = node.querySelector('ArticleTitle')?.textContent || 'Untitled';
        const journal = node.querySelector('Journal Title')?.textContent ||
            node.querySelector('MedlineTA')?.textContent || 'Unknown Journal';

        // Get publication date
        const pubDateNode = node.querySelector('PubDate');
        const year = pubDateNode?.querySelector('Year')?.textContent || '';
        const month = pubDateNode?.querySelector('Month')?.textContent || '';
        const pubDate = month ? `${month} ${year}` : year;

        // Get publication types
        const pubTypeNodes = node.querySelectorAll('PublicationType');
        const pubTypes: string[] = [];
        pubTypeNodes.forEach(pt => {
            if (pt.textContent) pubTypes.push(pt.textContent);
        });

        articles.push({
            pmid,
            title: title.replace(/<[^>]*>/g, ''), // Remove HTML tags
            source: journal,
            pubDate,
            pubTypes
        });
    });

    return articles;
}

function normalizeTitle(title: string): string {
    return title.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function isValidReference(ref: Reference): boolean {
    if (!ref.pubmedId || !ref.title) return false;
    const normalizedTitle = normalizeTitle(ref.title);
    if (!normalizedTitle || normalizedTitle === 'untitled') return false;
    return true;
}

function dedupeReferences(references: Reference[]): Reference[] {
    const seen = new Set<string>();
    const output: Reference[] = [];

    for (const ref of references) {
        const key = ref.pubmedId ? `pmid:${ref.pubmedId}` : `title:${normalizeTitle(ref.title)}`;
        if (!key || seen.has(key)) continue;
        seen.add(key);
        output.push(ref);
    }

    return output;
}

/**
 * Determine evidence type from publication types
 */
function getEvidenceType(pubTypes: string[]): string {
    const typeStr = pubTypes.join(' ').toLowerCase();
    if (typeStr.includes('meta-analysis')) return 'Meta-Analysis';
    if (typeStr.includes('systematic review')) return 'Systematic Review';
    if (typeStr.includes('randomized controlled trial')) return 'RCT';
    if (typeStr.includes('clinical trial')) return 'Clinical Trial';
    if (typeStr.includes('guideline')) return 'Guideline';
    if (typeStr.includes('review')) return 'Review';
    return 'Article';
}

/**
 * Estimate relevance based on publication type
 */
function estimateRelevance(pubTypes: string[]): 'High' | 'Medium' | 'Low' {
    const typeStr = pubTypes.join(' ').toLowerCase();
    if (typeStr.includes('meta-analysis') || typeStr.includes('systematic review') || typeStr.includes('guideline')) {
        return 'High';
    }
    if (typeStr.includes('randomized controlled trial') || typeStr.includes('clinical trial')) {
        return 'Medium';
    }
    return 'Low';
}

// --- Main Public Functions ---

/**
 * Search PubMed using PICO framework with progressive fallback.
 * Strategy 1: Full keyword query (P + I + O)
 * Strategy 2: Patient + Intervention only
 * Strategy 3: Core keywords without study-type filter
 */
export interface SearchResult {
    references: Reference[];
    strategyUsed: number;
    queryUsed: string;
}

export async function searchPubMed(pico: PicoData): Promise<Reference[]> {
    const result = await searchPubMedWithMeta(pico);
    return result.references;
}

/**
 * Search with metadata about which strategy succeeded.
 * Used by the retry/refinement mechanism.
 */
export async function searchPubMedWithMeta(pico: PicoData): Promise<SearchResult> {
    // Strategy 1: Full PICO phrase-based query
    try {
        const query1 = picoToSearchQuery(pico);
        console.log('[PubMed] Strategy 1:', query1);
        const results1 = await searchPubMedByQuery(query1);
        if (results1.length > 0) return { references: results1, strategyUsed: 1, queryUsed: query1 };
    } catch (e) { console.warn('[PubMed] Strategy 1 failed:', e); }

    // Strategy 2: Patient + Intervention phrases (drop Outcome, broader study types)
    try {
        const pWords = extractKeywords(pico.patient, 3);
        const iWords = extractKeywords(pico.intervention, 3);
        if (pWords.length > 0 && iWords.length > 0) {
            const tenYearsAgo = new Date().getFullYear() - 10;
            const query2 = `(${pWords.map(w => `"${w}"[tiab]`).join(' OR ')}) AND (${iWords.map(w => `"${w}"[tiab]`).join(' OR ')}) AND ${tenYearsAgo}:3000[dp]`;
            console.log('[PubMed] Strategy 2:', query2);
            const results2 = await searchPubMedByQuery(query2);
            if (results2.length > 0) return { references: results2, strategyUsed: 2, queryUsed: query2 };
        }
    } catch (e) { console.warn('[PubMed] Strategy 2 failed:', e); }

    // Strategy 3: Broadest — just core condition + intervention terms, no date/type filters
    try {
        const allWords = [
            ...extractKeywords(pico.patient, 2),
            ...extractKeywords(pico.intervention, 2)
        ];
        if (allWords.length > 0) {
            const query3 = allWords.map(w => `"${w}"[tiab]`).join(' AND ');
            console.log('[PubMed] Strategy 3:', query3);
            const results3 = await searchPubMedByQuery(query3);
            if (results3.length > 0) return { references: results3, strategyUsed: 3, queryUsed: query3 };
        }
    } catch (e) { console.warn('[PubMed] Strategy 3 failed:', e); }

    // Strategy 4: MeSH terms instead of [tiab] — much broader coverage
    try {
        const pWords = extractKeywords(pico.patient, 2);
        const iWords = extractKeywords(pico.intervention, 2);
        const allTerms = [...pWords, ...iWords].filter(w => w.length > 3);
        if (allTerms.length > 0) {
            const query4 = allTerms.map(w => `${w}[All Fields]`).join(' AND ');
            console.log('[PubMed] Strategy 4 (All Fields):', query4);
            const results4 = await searchPubMedByQuery(query4);
            if (results4.length > 0) return { references: results4, strategyUsed: 4, queryUsed: query4 };
        }
    } catch (e) { console.warn('[PubMed] Strategy 4 failed:', e); }

    // Strategy 5: Simple free-text from PICO patient + intervention (broadest possible)
    try {
        const simpleTerms = [pico.patient, pico.intervention]
            .join(' ')
            .replace(/[^\w\s]/g, ' ')
            .split(/\s+/)
            .map(w => w.toLowerCase())
            .filter(w => w.length > 4 && !STOP_WORDS.has(w))
            .slice(0, 3);
        if (simpleTerms.length > 0) {
            const query5 = simpleTerms.join(' AND ');
            console.log('[PubMed] Strategy 5 (simple):', query5);
            const results5 = await searchPubMedByQuery(query5);
            if (results5.length > 0) return { references: results5, strategyUsed: 5, queryUsed: query5 };
        }
    } catch (e) { console.warn('[PubMed] Strategy 5 failed:', e); }

    return { references: [], strategyUsed: 0, queryUsed: '' };
}

/**
 * Search PubMed with custom search terms provided by the user or AI.
 * Used for the retry/refinement flow.
 */
export async function searchPubMedCustomTerms(terms: string[]): Promise<Reference[]> {
    if (terms.length === 0) return [];
    const query = terms.map(t => t.includes(' ') ? `"${t}"[tiab]` : `${t}[All Fields]`).join(' AND ');
    console.log('[PubMed] Custom terms query:', query);
    return searchPubMedByQuery(query);
}

/**
 * Search PubMed with a raw query string
 * Implements caching and error handling
 */
export async function searchPubMedByQuery(query: string): Promise<Reference[]> {
    // Check cache first
    const cached = getFromCache(query);
    if (cached) {
        console.log('[PubMed] Returning cached results for query');
        return cached;
    }

    try {
        // Search for PMIDs
        const pmids = await esearch(query);
        if (pmids.length === 0) {
            return [];
        }

        // Fetch article details
        const articles = await efetch(pmids);

        // Convert to Reference format
        const references: Reference[] = articles.map((article) => ({
            id: `pubmed-${article.pmid}`,
            title: article.title,
            source: article.source,
            year: article.pubDate,
            type: getEvidenceType(article.pubTypes),
            relevance: estimateRelevance(article.pubTypes),
            pubmedId: article.pmid,
            url: `https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`
        }));

        const verifiedReferences = dedupeReferences(references.filter(isValidReference));

        // Cache results
        saveToCache(query, verifiedReferences);

        return verifiedReferences;
    } catch (error) {
        console.error('[PubMed] Search error:', error);
        throw error;
    }
}

/**
 * Generate a simple search query from free text
 * Fallback when PICO is incomplete
 */
export async function searchPubMedSimple(text: string): Promise<Reference[]> {
    // Extract key medical terms (basic extraction)
    const cleaned = text
        .replace(/[^\w\s]/g, ' ')
        .split(/\s+/)
        .filter(word => word.length > 3)
        .slice(0, 5)
        .join(' AND ');

    const query = `${cleaned} AND (randomized controlled trial[pt] OR meta-analysis[pt] OR systematic review[pt])`;
    return searchPubMedByQuery(query);
}
