# Legal Playbook Configuration

## Workspace Defaults

- Primary jurisdiction: Korea
- Review language: ko-KR
- Local venue tokens: korea, republic of korea, seoul
- Compliance profile: vendor_saas
- Compliance clauses: Data Protection, Term and Termination, Governing Law, Dispute Resolution, NDA Mutuality, NDA Term, NDA Carveouts
- Compliance clauses vendor saas: Data Protection, Term and Termination, Governing Law, Dispute Resolution, NDA Mutuality, NDA Term, NDA Carveouts
- Compliance clauses nda: NDA Mutuality, NDA Term, NDA Carveouts, Governing Law, Dispute Resolution
- Compliance clauses privacy: Data Protection, Governing Law, Dispute Resolution
- Fallback policy: If the playbook and document evidence do not align, use a conservative review posture and escalate for legal review.

### Limitation of Liability
- Keywords: limitation of liability, liability cap, cap on liability, liability limitation, consequential damages
- Favorable signals: mutual liability cap, mutual cap, fees paid, fees payable, direct damages only
- Standard position: Use a mutual liability cap tied to contract value and carve out only narrow high-risk categories.
- Acceptable range: A cap tied to fees paid or payable is acceptable when the carveouts remain narrow and symmetrical.
- Fallback position: If a full mutual cap is unavailable, cap direct damages at fees paid in the prior 12 months and keep ordinary carveouts narrow.
- Redline suggestion: Replace any uncapped general liability with a mutual cap tied to fees and carve out only confidentiality, IP infringement, fraud, and willful misconduct.
- Business impact: Uncapped or consequential-damages exposure can exceed contract value and distort pricing, reserve, and approval requirements.
- Negotiation priority: must-have
- Escalation trigger: unlimited liability
- Escalation trigger: uncapped liability
- Escalation trigger: consequential damages
- Escalation trigger: special damages

### Indemnification
- Keywords: indemnification, indemnity, hold harmless, indemnify, defense obligation
- Favorable signals: third-party claims, third party claims, prompt notice, defense control, cooperation
- Standard position: Keep indemnity limited to third-party claims tied to IP, privacy, or confidentiality breaches caused by the indemnifying party.
- Acceptable range: A claim-based indemnity with notice, defense control, and cooperation mechanics is acceptable.
- Fallback position: Limit indemnity to third-party claims and exclude indirect damages, internal claims, and open-ended defense obligations.
- Redline suggestion: Narrow indemnity to third-party IP, privacy, or confidentiality claims caused by the indemnifying party, with prompt notice and defense control.
- Business impact: Broad indemnity can shift defense costs and uncapped third-party exposure onto the business without matching insurance coverage.
- Negotiation priority: must-have
- Escalation trigger: unilateral indemnification
- Escalation trigger: uncapped indemnification
- Escalation trigger: first-party indemnity

### IP Ownership
- Keywords: intellectual property, ownership, assignment, license grant, work made for hire, background IP
- Favorable signals: retains background ip, retain background ip, customer data remains with the customer, limited license, purpose-bound license
- Standard position: Each party keeps pre-existing IP, customer data stays with the customer, and assignments are limited to expressly identified deliverables.
- Acceptable range: A limited, purpose-bound license is acceptable where outright ownership transfer is not.
- Fallback position: Preserve pre-existing IP and grant only a limited license for deliverables strictly necessary to receive the service.
- Redline suggestion: Clarify that each party retains background IP, customer data remains with the customer, and any assignment is limited to bespoke deliverables expressly identified.
- Business impact: Overbroad assignment language can transfer core tooling, models, or know-how and block reuse across customers.
- Negotiation priority: must-have
- Escalation trigger: work made for hire
- Escalation trigger: broad assignment
- Escalation trigger: assignment of background IP

### Data Protection
- Keywords: data protection, privacy, personal data, processor, sub-processor, security, breach notification, transfer
- Favorable signals: dpa, processing instructions, breach notice, without undue delay, subprocessor notice, return or delete, delete or return
- Standard position: Require processing instructions, security commitments, breach notification, subprocessor controls, and deletion or return at end of term.
- Acceptable range: Equivalent controls are acceptable if they align with internal security and privacy requirements.
- Fallback position: Require a DPA, a bounded breach notice window, subprocessor notice, and safeguards for cross-border transfers.
- Redline suggestion: Add processing instructions, security commitments, breach notice without undue delay, approved subprocessor controls, and return-or-delete language.
- Business impact: Missing privacy controls creates regulatory, customer, and incident-response exposure that usually exceeds deal value.
- Negotiation priority: must-have
- Escalation trigger: no dpa
- Escalation trigger: cross-border transfer without safeguards
- Escalation trigger: without safeguards
- Escalation trigger: unrestricted data use
- Escalation trigger: breach notification after 30 days

### Term and Termination
- Keywords: term, termination, renewal, auto-renewal, termination for convenience, survival
- Favorable signals: termination for convenience, renewal notice, advance notice, initial term, survival only
- Standard position: Contract term, renewal, and termination rights should be explicit and commercially workable for both parties.
- Acceptable range: An initial lock-in is acceptable if the renewal notice and exit path remain reasonable.
- Fallback position: Permit termination for convenience after an initial lock-in period and require advance notice for auto-renewal.
- Redline suggestion: Add a reasonable notice period before renewal, termination for convenience after the initial term, and survival only for genuinely post-termination obligations.
- Business impact: One-sided renewal and weak exit rights can trap budget, delay vendor change, and increase operational dependency.
- Negotiation priority: should-have
- Escalation trigger: auto-renewal without notice
- Escalation trigger: no termination for convenience
- Escalation trigger: perpetual survival

### Governing Law
- Keywords: governing law, jurisdiction, venue, forum, choice of law
- Favorable signals: neutral forum, mutually acceptable venue, mutually acceptable law, commercially neutral forum
- Standard position: Use a venue and governing law that the business can practically access and enforce.
- Acceptable range: A commercially neutral forum is acceptable if dispute cost and enforcement remain manageable.
- Fallback position: Use a commercially neutral forum that the business can practically access and enforce.
- Redline suggestion: Replace non-standard or unfavorable venue language with a mutually workable governing law and venue, or carve disputes into a neutral arbitration seat.
- Business impact: Remote or unfavorable venue terms increase litigation cost, reduce leverage, and complicate enforcement.
- Negotiation priority: should-have
- Escalation trigger: non-standard jurisdiction
- Escalation trigger: mandatory arbitration in unfavorable venue
- Escalation trigger: foreign governing law

### Dispute Resolution
- Keywords: dispute resolution, arbitration, litigation, injunctive relief, venue, forum
- Favorable signals: mutual injunctive relief, interim relief mutual, neutral arbitration seat, balanced arbitration rules
- Standard position: Dispute procedures should be symmetrical, clear, and proportionate to deal size and risk.
- Acceptable range: Arbitration is acceptable when the venue, rules, and interim relief rights remain balanced.
- Fallback position: Keep dispute procedures symmetrical and avoid mandatory foreign arbitration unless the commercial upside clearly justifies it.
- Redline suggestion: Make interim relief mutual, define venue and rules clearly, and remove unilateral or foreign-only dispute mechanisms.
- Business impact: One-sided injunction rights or remote arbitration can raise cost and reduce practical ability to enforce rights quickly.
- Negotiation priority: should-have
- Escalation trigger: one-sided injunctive relief
- Escalation trigger: mandatory foreign arbitration
- Escalation trigger: unilateral venue

### NDA Mutuality
- Keywords: confidential information, non-disclosure, confidentiality, confidential, one-way nda
- Favorable signals: mutual confidentiality, both parties, each party, disclosing party and receiving party
- Standard position: Confidentiality obligations should be mutual unless a documented one-way flow clearly justifies otherwise.
- Acceptable range: A one-way NDA is acceptable only when the information flow is genuinely one-directional and the rationale is documented.
- Fallback position: If one-way confidentiality is unavoidable, document the business reason and narrow the receiving party obligations to the specific disclosure flow.
- Redline suggestion: Convert confidentiality obligations to mutual form and align use, care, and disclosure limits for both sides.
- Business impact: One-way NDA language can leave the business exposed when it shares roadmap, pricing, or technical material during diligence.
- Negotiation priority: must-have
- Escalation trigger: one-way only
- Escalation trigger: only to recipient
- Escalation trigger: only to customer
- Escalation trigger: applies only to recipient
- Escalation trigger: applies only to customer
- Escalation trigger: unilateral confidentiality
- Escalation trigger: reverse engineering permitted

### NDA Term
- Keywords: term, survival, years, confidentiality term, duration
- Favorable signals: 2 years, 3 years, trade secrets, source code, finite confidentiality term
- Standard position: Use a finite confidentiality period for ordinary information and reserve longer protection only for trade secrets or source code.
- Acceptable range: The survival period can vary by information type if the structure remains clear and enforceable.
- Fallback position: Use differentiated survival periods by information type instead of perpetual coverage for all disclosures.
- Redline suggestion: Set a finite confidentiality term for ordinary information and reserve longer protection only for trade secrets or source code.
- Business impact: Perpetual or very short terms both create operational problems: one over-restricts the business, the other weakens protection.
- Negotiation priority: should-have
- Escalation trigger: perpetual confidentiality for all information
- Escalation trigger: term less than 1 year
- Escalation trigger: perpetual protection for all data

### NDA Carveouts
- Keywords: publicly available, independently developed, rightfully received, carveout, carve-outs, compelled disclosure
- Favorable signals: publicly available, independently developed, rightfully received, compelled disclosure, notice process
- Standard position: Standard carveouts should cover public-domain, independently developed, and rightfully received information, plus compelled disclosures with notice.
- Acceptable range: Equivalent carveout wording is acceptable if the substantive exceptions remain intact.
- Fallback position: Preserve the standard public-domain, independent-development, and rightfully-received exceptions even if wording is tightened.
- Redline suggestion: Add the standard carveouts expressly and align them with a compelled-disclosure notice process.
- Business impact: Missing carveouts can prevent ordinary business operations and create breach risk for information the business did not misuse.
- Negotiation priority: must-have
- Escalation trigger: no carveouts
- Escalation trigger: no carve-outs
- Escalation trigger: no carve outs
- Escalation trigger: carveouts omitted
- Escalation trigger: no compelled disclosure process

### NDA Residuals
- Keywords: residuals, retained in memory, memory exception, residual clause
- Favorable signals: no residuals, residuals deleted, trade secrets excluded, deliberate retention prohibited
- Standard position: Do not accept broad residuals language that undercuts confidentiality protection.
- Acceptable range: A tightly limited residuals concept is acceptable only if it excludes deliberate retention, source code, and trade secrets.
- Fallback position: If residuals cannot be deleted, limit them to generalized memory, prohibit deliberate retention, and preserve trade-secret protections.
- Redline suggestion: Remove the residuals clause, or narrowly define it so it does not permit use of confidential information, source code, or trade secrets.
- Business impact: Residuals language can hollow out confidentiality protection and weaken enforcement against later reuse of protected know-how.
- Negotiation priority: must-have
- Escalation trigger: residuals clause
- Escalation trigger: memory exception
- Escalation trigger: retained in memory
