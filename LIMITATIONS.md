# Known Limitations

## Model Limitations

### PICO Extraction
- May not correctly parse complex clinical scenarios with multiple conditions
- Requires explicit statement of comparison; defaults to "standard care" when unclear
- Completeness scoring is simplistic (25% per field)

### Evidence Retrieval
- **PubMed only** - Does not search Cochrane, NICE, UpToDate, or specialty databases
- **Abstracts only** - Cannot parse full-text articles
- **English only** - Non-English literature is excluded
- **Recency bias** - Filters to last 10 years by default
- **Study type filters** - May miss relevant observational studies

### AI Response Quality
- Responses may lack specificity for rare conditions
- May not catch subtle differences between similar drugs or interventions
- Cannot verify that retrieved evidence applies to specific patient populations
- May miss critical safety warnings or black box warnings

## Technical Limitations

### Performance
- PubMed API rate limited to 3 requests/second
- Large chat histories may slow response times
- Image analysis requires multimodal model (4B or 27B-MM)

### Browser Compatibility
- Tested on Chrome, Firefox, Safari (latest versions)
- LocalStorage required for caching
- WebSocket not supported (no streaming responses)

### Deployment
- Frontend-only caching (no server-side persistence)
- API keys exposed in client-side code (demo only)
- No offline support

## Data Limitations

- **No real patient data** - Demo only with synthetic cases
- **No EHR integration** - Cannot pull real clinical information
- **No prescription/ordering** - Outputs are purely informational
- **No follow-up tracking** - Results phase is demonstrative only

## Scope Limitations

### What MVP Does NOT Include
- Transcription/voice input (planned but not implemented)
- Multi-provider collaboration
- Guideline database integration
- Drug interaction checking
- Clinical decision support alerts
- Export to EHR formats (FHIR, HL7)

---

*These limitations are documented for transparency and should be addressed before any clinical deployment.*
