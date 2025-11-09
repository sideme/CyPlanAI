"""
Seed Data Service - Populates initial frameworks and prompts
"""
from models import db, Framework, Prompt, Control, Threat, ControlMapping

def seed_frameworks_and_prompts():
    """Seed initial frameworks and prompts if they don't exist"""
    
    # Check if frameworks already exist
    if Framework.query.count() > 0:
        return
    
    # Create NIST CSF Framework
    nist_csf = Framework(
        frameworkId='nist-csf-001',
        name='NIST Cybersecurity Framework',
        type='NIST_CSF',
        description='A voluntary framework based on existing standards, guidelines, and practices for organizations to better manage and reduce cybersecurity risk.',
        version='1.1'
    )
    db.session.add(nist_csf)
    
    # Create ISO 27001 Framework
    iso_27001 = Framework(
        frameworkId='iso-27001-001',
        name='ISO/IEC 27001:2013',
        type='ISO_27001',
        description='An international standard for managing information security that specifies requirements for establishing, implementing, maintaining, and continually improving an information security management system.',
        version='2013'
    )
    db.session.add(iso_27001)
    
    # Create NIST AI RMF Framework
    nist_ai_rmf = Framework(
        frameworkId='nist-ai-rmf-001',
        name='NIST AI Risk Management Framework',
        type='NIST_AI_RMF',
        description='A framework to help organizations manage risks associated with AI systems.',
        version='1.0'
    )
    db.session.add(nist_ai_rmf)
    
    # Create MITRE ATLAS Framework
    mitre_atlas = Framework(
        frameworkId='mitre-atlas-001',
        name='MITRE ATLAS',
        type='MITRE_ATLAS',
        description='Adversarial Threat Landscape for Artificial-Intelligence Systems - a knowledge base of adversary tactics and techniques for AI systems.',
        version='1.0'
    )
    db.session.add(mitre_atlas)
    
    db.session.commit()
    
    # Seed comprehensive controls from frameworks
    controls = [
        # NIST CSF Controls
        Control(
            frameworkId=nist_csf.frameworkId,
            reference='PR.AC-3',
            title='Access control least privilege',
            description='Remote access is managed. Ensure least privilege and separation of duties for all users.',
            category='Protect',
            maturity_cost=2,
            severity_mitigated=4,
        ),
        Control(
            frameworkId=nist_csf.frameworkId,
            reference='PR.IP-1',
            title='Baseline configuration',
            description='Baseline configurations of information technology/industrial control systems are created and maintained incorporating security.',
            category='Protect',
            maturity_cost=3,
            severity_mitigated=4,
        ),
        Control(
            frameworkId=nist_csf.frameworkId,
            reference='DE.AE-1',
            title='Baseline network operations',
            description='A baseline of network operations and expected data flows for users and systems is established and managed.',
            category='Detect',
            maturity_cost=3,
            severity_mitigated=3,
        ),
        # ISO 27001 Controls
        Control(
            frameworkId=iso_27001.frameworkId,
            reference='A.8.1.1',
            title='Inventory of assets',
            description='Assets associated with information and information processing facilities shall be identified and an inventory of these assets shall be drawn up and maintained.',
            category='Asset Management',
            maturity_cost=2,
            severity_mitigated=3,
        ),
        Control(
            frameworkId=iso_27001.frameworkId,
            reference='A.9.2.1',
            title='User access management',
            description='User access rights to networks and network services should be controlled via a formal user access management process.',
            category='Access Control',
            maturity_cost=2,
            severity_mitigated=4,
        ),
        Control(
            frameworkId=iso_27001.frameworkId,
            reference='A.12.6.1',
            title='Management of technical vulnerabilities',
            description='Information about technical vulnerabilities of information systems being used shall be obtained in a timely fashion, the organization\'s exposure to such vulnerabilities evaluated and appropriate measures taken to address the associated risk.',
            category='Operations Security',
            maturity_cost=3,
            severity_mitigated=4,
        ),
        # NIST AI RMF Controls
        Control(
            frameworkId=nist_ai_rmf.frameworkId,
            reference='GOV-1',
            title='AI risk governance',
            description='Establish governance structures and processes to manage AI risks across the organization.',
            category='Governance',
            maturity_cost=3,
            severity_mitigated=4,
        ),
        Control(
            frameworkId=nist_ai_rmf.frameworkId,
            reference='MAP-2',
            title='Adversarial risks',
            description='Identify and assess adversarial risks including data poisoning, model evasion, and extraction attacks.',
            category='Mapping',
            maturity_cost=2,
            severity_mitigated=4,
        ),
    ]
    for c in controls:
        db.session.add(c)

    # Add prompts for NIST CSF
    nist_prompts = [
        Prompt(
            frameworkId=nist_csf.frameworkId,
            text='Describe your organization\'s current approach to identifying cybersecurity risks. What assets and systems need protection?',
            category='Identify',
            order=1
        ),
        Prompt(
            frameworkId=nist_csf.frameworkId,
            text='What protective measures (controls) do you currently have in place? Describe your security policies and procedures.',
            category='Protect',
            order=2
        ),
        Prompt(
            frameworkId=nist_csf.frameworkId,
            text='How do you currently detect cybersecurity events? What monitoring and detection capabilities exist?',
            category='Detect',
            order=3
        ),
        Prompt(
            frameworkId=nist_csf.frameworkId,
            text='Describe your incident response procedures. How does your organization respond to cybersecurity incidents?',
            category='Respond',
            order=4
        ),
        Prompt(
            frameworkId=nist_csf.frameworkId,
            text='What recovery planning and improvement processes do you have to restore capabilities and services after an incident?',
            category='Recover',
            order=5
        ),
    ]
    
    for prompt in nist_prompts:
        db.session.add(prompt)
    
    # Add prompts for ISO 27001
    iso_prompts = [
        Prompt(
            frameworkId=iso_27001.frameworkId,
            text='Describe your organization\'s information security objectives and scope of the ISMS.',
            category='Context and Scope',
            order=1
        ),
        Prompt(
            frameworkId=iso_27001.frameworkId,
            text='What risks to information security has your organization identified? Describe your risk assessment process.',
            category='Risk Assessment',
            order=2
        ),
        Prompt(
            frameworkId=iso_27001.frameworkId,
            text='What information security controls are currently implemented? Reference relevant ISO 27001 Annex A controls if applicable.',
            category='Control Implementation',
            order=3
        ),
        Prompt(
            frameworkId=iso_27001.frameworkId,
            text='How is information security monitored, measured, and evaluated in your organization?',
            category='Monitoring and Measurement',
            order=4
        ),
        Prompt(
            frameworkId=iso_27001.frameworkId,
            text='Describe your approach to continual improvement of the information security management system.',
            category='Continual Improvement',
            order=5
        ),
    ]
    
    for prompt in iso_prompts:
        db.session.add(prompt)
    
    # Add prompts for NIST AI RMF
    ai_rmf_prompts = [
        Prompt(
            frameworkId=nist_ai_rmf.frameworkId,
            text='Describe the AI system(s) you plan to deploy or currently use. What are their intended purposes and applications?',
            category='AI System Context',
            order=1
        ),
        Prompt(
            frameworkId=nist_ai_rmf.frameworkId,
            text='What potential risks and harms are associated with your AI systems? Consider accuracy, fairness, privacy, and security risks.',
            category='AI Risk Identification',
            order=2
        ),
        Prompt(
            frameworkId=nist_ai_rmf.frameworkId,
            text='What governance and oversight mechanisms do you have for AI systems? Describe accountability structures.',
            category='AI Governance',
            order=3
        ),
        Prompt(
            frameworkId=nist_ai_rmf.frameworkId,
            text='How do you ensure the reliability, accuracy, and trustworthiness of your AI systems throughout their lifecycle?',
            category='AI System Reliability',
            order=4
        ),
    ]
    
    for prompt in ai_rmf_prompts:
        db.session.add(prompt)
    
    # Add prompts for MITRE ATLAS
    atlas_prompts = [
        Prompt(
            frameworkId=mitre_atlas.frameworkId,
            text='What adversarial threats are you most concerned about for your AI systems? (e.g., model evasion, data poisoning, model extraction)',
            category='Adversarial Threats',
            order=1
        ),
        Prompt(
            frameworkId=mitre_atlas.frameworkId,
            text='Describe your AI system\'s attack surface. What components are exposed to potential adversaries?',
            category='Attack Surface',
            order=2
        ),
        Prompt(
            frameworkId=mitre_atlas.frameworkId,
            text='What defensive measures do you have in place to protect AI systems from adversarial attacks?',
            category='AI Defense',
            order=3
        ),
        Prompt(
            frameworkId=mitre_atlas.frameworkId,
            text='How do you detect and respond to adversarial activities targeting your AI systems?',
            category='Adversarial Detection and Response',
            order=4
        ),
    ]
    
    for prompt in atlas_prompts:
        db.session.add(prompt)
    
    # Comprehensive threat library (incl. adversarial ML)
    threats = [
        Threat(
            name='Phishing leading to credential theft',
            description='Social-engineering emails or messages designed to trick users into revealing credentials or installing malware.',
            category='Social Engineering', likelihood=4, impact=4
        ),
        Threat(
            name='Data poisoning (ML)',
            description='Adversary injects crafted samples into training data to corrupt model behavior, leading to misclassifications or backdoors.',
            category='Adversarial ML', likelihood=2, impact=5
        ),
        Threat(
            name='Model evasion attacks',
            description='Adversarial examples crafted to fool ML models at inference time, causing incorrect predictions.',
            category='Adversarial ML', likelihood=3, impact=4
        ),
        Threat(
            name='Model extraction',
            description='Attackers query a deployed model extensively to reconstruct its parameters or training data.',
            category='Adversarial ML', likelihood=2, impact=3
        ),
        Threat(
            name='Ransomware',
            description='Malware that encrypts files and demands payment for decryption keys.',
            category='Malware', likelihood=3, impact=5
        ),
        Threat(
            name='Unauthorized access',
            description='Gaining access to systems or data without proper authorization through vulnerabilities or weak authentication.',
            category='Access Control', likelihood=3, impact=4
        ),
        Threat(
            name='Data breach',
            description='Unauthorized access and exfiltration of sensitive data.',
            category='Data Security', likelihood=3, impact=5
        ),
    ]
    for t in threats:
        db.session.add(t)

    db.session.commit()

    # Map threats to controls (ontology edges) - comprehensive mappings
    pr_ac3 = Control.query.filter_by(reference='PR.AC-3').first()
    pr_ip1 = Control.query.filter_by(reference='PR.IP-1').first()
    de_ae1 = Control.query.filter_by(reference='DE.AE-1').first()
    a811 = Control.query.filter_by(reference='A.8.1.1').first()
    a921 = Control.query.filter_by(reference='A.9.2.1').first()
    a1261 = Control.query.filter_by(reference='A.12.6.1').first()
    gov1 = Control.query.filter_by(reference='GOV-1').first()
    map2 = Control.query.filter_by(reference='MAP-2').first()
    
    phishing = Threat.query.filter_by(name='Phishing leading to credential theft').first()
    poisoning = Threat.query.filter_by(name='Data poisoning (ML)').first()
    evasion = Threat.query.filter_by(name='Model evasion attacks').first()
    extraction = Threat.query.filter_by(name='Model extraction').first()
    ransomware = Threat.query.filter_by(name='Ransomware').first()
    unauthorized = Threat.query.filter_by(name='Unauthorized access').first()
    breach = Threat.query.filter_by(name='Data breach').first()
    
    # Phishing mappings
    if pr_ac3 and phishing:
        db.session.add(ControlMapping(threatId=phishing.threatId, controlId=pr_ac3.controlId,
                                      evidence_hint='Access reviews, RBAC policy, privileged access approvals'))
    if a921 and phishing:
        db.session.add(ControlMapping(threatId=phishing.threatId, controlId=a921.controlId,
                                      evidence_hint='User access management procedures, authentication logs'))
    
    # Data poisoning mappings
    if a811 and poisoning:
        db.session.add(ControlMapping(threatId=poisoning.threatId, controlId=a811.controlId,
                                      evidence_hint='Asset inventory including data lineage and dataset approval logs'))
    if map2 and poisoning:
        db.session.add(ControlMapping(threatId=poisoning.threatId, controlId=map2.controlId,
                                      evidence_hint='Adversarial risk assessment, training data validation procedures'))
    
    # Model evasion mappings
    if map2 and evasion:
        db.session.add(ControlMapping(threatId=evasion.threatId, controlId=map2.controlId,
                                      evidence_hint='Adversarial testing results, model robustness evaluations'))
    if de_ae1 and evasion:
        db.session.add(ControlMapping(threatId=evasion.threatId, controlId=de_ae1.controlId,
                                      evidence_hint='Anomaly detection logs, model inference monitoring'))
    
    # Ransomware mappings
    if pr_ip1 and ransomware:
        db.session.add(ControlMapping(threatId=ransomware.threatId, controlId=pr_ip1.controlId,
                                      evidence_hint='Baseline configurations, system hardening documentation'))
    if a1261 and ransomware:
        db.session.add(ControlMapping(threatId=ransomware.threatId, controlId=a1261.controlId,
                                      evidence_hint='Vulnerability scanning reports, patch management records'))
    
    # Unauthorized access mappings
    if pr_ac3 and unauthorized:
        db.session.add(ControlMapping(threatId=unauthorized.threatId, controlId=pr_ac3.controlId,
                                      evidence_hint='Access control lists, authentication mechanisms'))
    if a921 and unauthorized:
        db.session.add(ControlMapping(threatId=unauthorized.threatId, controlId=a921.controlId,
                                      evidence_hint='User access management policies, access review logs'))
    
    # Data breach mappings
    if pr_ac3 and breach:
        db.session.add(ControlMapping(threatId=breach.threatId, controlId=pr_ac3.controlId,
                                      evidence_hint='Access logs, data classification documentation'))
    if de_ae1 and breach:
        db.session.add(ControlMapping(threatId=breach.threatId, controlId=de_ae1.controlId,
                                      evidence_hint='Network monitoring logs, data flow analysis'))

    db.session.commit()
    print("Seed data populated successfully")

