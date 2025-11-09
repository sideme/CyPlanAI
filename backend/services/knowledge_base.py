"""
Knowledge Base Service - Provides RAG context from frameworks, controls, threats
Enhanced with vector search for library documents
"""
from typing import List, Dict, Any, Optional
from models import Framework, Control, Threat, ControlMapping
from services.document_loader import DocumentLoader


class KnowledgeBase:
    """Retrieval-Augmented Generation knowledge base for cybersecurity frameworks"""
    
    _document_loader: Optional[DocumentLoader] = None
    
    @classmethod
    def _get_document_loader(cls) -> DocumentLoader:
        """Lazy initialization of document loader"""
        if cls._document_loader is None:
            try:
                cls._document_loader = DocumentLoader()
            except Exception as e:
                print(f"Warning: Could not initialize document loader: {e}")
                cls._document_loader = None
        return cls._document_loader

    @staticmethod
    def get_all_knowledge() -> str:
        """Get all knowledge as formatted text for RAG context"""
        parts = []

        # Frameworks overview
        frameworks = Framework.query.all()
        parts.append("=== CYBERSECURITY FRAMEWORKS ===\n")
        for fw in frameworks:
            parts.append(f"Framework: {fw.name} ({fw.type})\n")
            parts.append(f"Description: {fw.description or 'N/A'}\n")
            parts.append(f"Version: {fw.version or 'N/A'}\n\n")

        # Controls from all frameworks
        parts.append("=== CONTROLS ===\n")
        controls = Control.query.order_by(Control.frameworkId, Control.reference).all()
        for ctrl in controls:
            fw = Framework.query.get(ctrl.frameworkId)
            parts.append(f"Control: {ctrl.reference} - {ctrl.title}\n")
            parts.append(f"Framework: {fw.name if fw else 'Unknown'}\n")
            parts.append(f"Category: {ctrl.category or 'N/A'}\n")
            parts.append(f"Description: {ctrl.description or 'N/A'}\n")
            parts.append(f"Maturity/Cost: {ctrl.maturity_cost}/5, Severity Mitigated: {ctrl.severity_mitigated}/5\n\n")

        # Threats
        parts.append("=== THREAT LIBRARY ===\n")
        threats = Threat.query.all()
        for t in threats:
            parts.append(f"Threat: {t.name}\n")
            parts.append(f"Category: {t.category or 'N/A'}\n")
            parts.append(f"Description: {t.description or 'N/A'}\n")
            parts.append(f"Likelihood: {t.likelihood}/5, Impact: {t.impact}/5\n")

            # Related controls
            mappings = ControlMapping.query.filter_by(threatId=t.threatId).all()
            if mappings:
                parts.append("Recommended Controls:\n")
                for m in mappings:
                    c = m.control
                    if c:
                        parts.append(f"  - {c.reference} ({c.title}): {m.evidence_hint or 'See control description'}\n")
            parts.append("\n")

        return "\n".join(parts)

    @staticmethod
    def search_knowledge(query: str) -> str:
        """Search knowledge base for relevant information (simple keyword matching)"""
        query_lower = query.lower()
        results = []

        # Search frameworks
        frameworks = Framework.query.filter(
            (Framework.name.ilike(f'%{query}%')) |
            (Framework.description.ilike(f'%{query}%'))
        ).all()
        if frameworks:
            results.append("=== RELEVANT FRAMEWORKS ===\n")
            for fw in frameworks:
                results.append(f"{fw.name}: {fw.description}\n")

        # Search controls
        controls = Control.query.filter(
            (Control.title.ilike(f'%{query}%')) |
            (Control.description.ilike(f'%{query}%')) |
            (Control.reference.ilike(f'%{query}%')) |
            (Control.category.ilike(f'%{query}%'))
        ).all()
        if controls:
            results.append("\n=== RELEVANT CONTROLS ===\n")
            for c in controls:
                fw = Framework.query.get(c.frameworkId)
                results.append(f"{c.reference} ({fw.name if fw else 'Unknown'}): {c.title}\n")
                if c.description:
                    results.append(f"  {c.description}\n")

        # Search threats
        threats = Threat.query.filter(
            (Threat.name.ilike(f'%{query}%')) |
            (Threat.description.ilike(f'%{query}%')) |
            (Threat.category.ilike(f'%{query}%'))
        ).all()
        if threats:
            results.append("\n=== RELEVANT THREATS ===\n")
            for t in threats:
                results.append(f"{t.name} ({t.category}): {t.description}\n")

        return "\n".join(results) if results else "No specific matches found in knowledge base."

    @staticmethod
    def get_context_for_question(question: str, use_vector_search: bool = True) -> str:
        """Get relevant context for a user question using keyword extraction and vector search"""
        context_parts = []
        
        # 1. Vector search in library documents (if available)
        if use_vector_search:
            try:
                doc_loader = KnowledgeBase._get_document_loader()
                if doc_loader:
                    vector_results = doc_loader.search(query=question, n_results=3)
                    if vector_results:
                        context_parts.append("=== RELEVANT LIBRARY DOCUMENTATION ===\n")
                        for result in vector_results:
                            source = result['metadata'].get('source', 'Unknown')
                            library = result['metadata'].get('library', 'default')
                            context_parts.append(f"[From {library}/{source}]\n{result['content']}\n\n")
            except Exception as e:
                print(f"Vector search error: {e}")
        
        # 2. Traditional keyword-based search in frameworks/controls/threats
        keywords = []
        q_lower = question.lower()

        # Framework names
        framework_names = ['nist csf', 'nist cs', 'iso 27001', 'iso27001', 'nist ai rmf', 'mitre atlas', 'atlas']
        for fw_name in framework_names:
            if fw_name in q_lower:
                keywords.append(fw_name)

        # Common threat terms
        threat_terms = ['phishing', 'poisoning', 'adversarial', 'attack', 'threat', 'risk', 'vulnerability']
        for term in threat_terms:
            if term in q_lower:
                keywords.append(term)

        # Control/security terms
        control_terms = ['control', 'compliance', 'audit', 'access', 'encryption', 'monitoring']
        for term in control_terms:
            if term in q_lower:
                keywords.append(term)

        # If specific keywords found, search; otherwise return general context
        if keywords:
            kb_context = KnowledgeBase.search_knowledge(" ".join(keywords))
            if kb_context:
                context_parts.append("=== CYBERSECURITY FRAMEWORK KNOWLEDGE ===\n")
                context_parts.append(kb_context)
        else:
            # Return summary of all knowledge (truncated for efficiency)
            all_knowledge = KnowledgeBase.get_all_knowledge()
            # Limit to first 3000 chars to avoid token limits
            context_parts.append("=== CYBERSECURITY FRAMEWORK KNOWLEDGE (Summary) ===\n")
            context_parts.append(all_knowledge[:3000])
        
        return "\n".join(context_parts) if context_parts else "No relevant context found."

