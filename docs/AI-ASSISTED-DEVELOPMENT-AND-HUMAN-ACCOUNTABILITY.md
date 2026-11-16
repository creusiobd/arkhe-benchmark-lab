# AI-Assisted Development and Human Accountability

**Project:** ARKHÉ Agent Boundary Defense Benchmark  
**Document version:** 0.1  
**Prepared:** 2026-11-16  
**Status:** Internal governance record; pending project-owner review  
**Owner:** Creusio Adolfo Gaspar Kizua  
**Purpose:** Transparently describe the use of AI-assisted development, identify the human decisions and responsibilities retained by the project owner, and define evidence and review controls.

> This document is a process disclosure, not a certification of code quality, an independent audit, a legal opinion, or a determination of eligibility for any grant program.

---

## 1. Executive statement

ARKHÉ is a founder-led defensive research and software project developed through AI-assisted and automated coding workflows.

The project owner reports that implementation code was produced through these workflows rather than by manually authoring every line. The owner supplied the project direction, problem framing, requirements, constraints, acceptance criteria, review feedback, and approval or rejection decisions throughout the development process.

The project owner remains accountable for the project's objectives, design decisions, accepted changes, test strategy, interpretation of evidence, public claims, third-party rights, and disclosures. AI assistance is treated as an implementation and reasoning aid, not as an independent reviewer, security auditor, research custodian, or substitute for human accountability.

This statement does **not** claim that every generated line was independently inspected, that every code path was manually reviewed, or that approval of an iteration proves its correctness. Those are separate verification activities and must be evidenced separately.

## 2. Scope and known development model

### 2.1 Project-owner account

Based on the project owner's account:

- The project is directed by one principal project owner/research lead.
- AI-assisted tools have been used to generate, modify, explain, and help test implementation code and supporting project materials.
- The project owner establishes the intended behavior, constraints, research questions, acceptance criteria, and priorities.
- The project owner evaluates outputs against those criteria and decides whether to accept, reject, or request revisions.
- The implementation process is therefore AI-assisted and human-directed; it should not be represented as exclusively manual software authorship.

This is a founder account of the working process. The repository does not currently contain a complete, independently verified, per-file or per-commit inventory of AI-generated contributions.

### 2.2 Tool and model inventory

The exact provider, product, model/version, date, and task are not yet recorded comprehensively for every historical code contribution. No tool names, model versions, contribution percentages, or line-level provenance should be invented retrospectively.

For future material changes, record the following when available:

| Field | Required record |
|---|---|
| Date | Date of the material development activity |
| Tool/provider | Product and provider used |
| Model/version | Exact model identifier when exposed |
| Task | What the tool was asked to do |
| Scope | Files, modules, tests, or documents materially affected |
| Human direction | Requirements, constraints, and acceptance criteria supplied |
| Human decision | Accepted, rejected, or revised; by whom |
| Verification | Commands, tests, CI runs, manual checks, or external review |
| Remaining uncertainty | What was not checked or independently verified |

Missing historical metadata must be marked **not recorded**. It must not be reconstructed from guesses.

## 3. Allocation of responsibilities

| Activity | AI-assisted tools | Project owner / human responsibility |
|---|---|---|
| Problem framing | May help explore or articulate options | Defines the problem, purpose, scope, and priorities |
| Requirements and acceptance criteria | May help structure or challenge them | Sets and approves the criteria |
| Architecture and design | May propose alternatives and draft designs | Chooses the design and owns trade-offs |
| Code implementation | Generates, edits, explains, or refactors code | Directs the task, evaluates changes, and decides what is accepted |
| Tests and test generation | May draft or execute tests | Defines what must be tested and evaluates whether the evidence is sufficient |
| Security analysis | May identify possible weaknesses | Does not treat AI output as an independent security audit; owns remediation decisions |
| Research analysis | May assist with calculations, summaries, and scripts | Owns protocol decisions, interpretation, limitations, and conclusions |
| Public and grant claims | May help draft wording | Verifies every claim against evidence and is responsible for the submitted representation |
| Release and publication | May automate workflows | Authorizes releases and remains accountable for published artifacts |

**Important distinction:** approving an AI-generated change against acceptance criteria is human oversight, but it is not automatically equivalent to line-by-line code review, independent peer review, penetration testing, or scientific validation.

## 4. Evidence currently present in the repository

The following artifacts provide evidence of project direction, engineering controls, and declared research boundaries. They do not, individually or collectively, prove that every implementation detail has been independently verified.

| Repository artifact | What it supports | What it does not prove |
|---|---|---|
| `README.md` | Project purpose, alpha status, architecture overview, evidence boundaries, and explicit non-claims | Production effectiveness or independent validation |
| `CONTRIBUTING.md` | Contribution workflow, defensive constraints, test instructions, and pull-request expectations | That every historical change followed every current instruction |
| `docs/anti_leakage_model.md` | Intended separation between runtime observations and evaluation ground truth, with named structural tests | A formal proof of zero leakage or absence of every possible defect |
| `docs/v0.6_preregistration.md` | Design-stage protocol, prohibited confirmatory claims, role separation, freeze gates, and open custodian/approver requirements | That v0.6 has been executed, independently custodied, or frozen |
| `docs/research_limitations.md` | Explicit methodological and operational limitations | Resolution of those limitations |
| `docs/research_risks.md` | Identified research, engineering, and operational risks and proposed mitigations | That every mitigation is implemented or independently tested |
| `docs/continuidade.md` | Project decisions and a record stating that the v0.6 application was submitted on 2026-11-10 | A submission receipt by itself; the actual confirmation should be retained separately |
| `proposal/form_answers_EN.md`, `proposal/form_answers_PT.md`, `proposal/ARKHE_CYBERSECURITY_GRANT_v0.6_EN.md`, and the grant badge in `README.md` | Application content and proposal framing | Their current status is consistent with the later submission record |

### 4.1 Repository consistency issue to resolve

At the current `main` snapshot, `docs/continuidade.md` records a v0.6 submission on 2026-11-10 and states that the application receipt was confirmed. However, the reviewed application answer files, English proposal brief, and README badge still describe the application as a draft or not submitted.

This is a documentation inconsistency. It must be reconciled in a separate, evidence-based update using the actual submission confirmation and the exact submitted version. This document does not silently resolve that discrepancy.

## 5. Verification model and limits

ARKHÉ uses automated tests, contracts, deterministic generation, CI workflows, and evaluation separation as engineering controls. These are valuable forms of evidence, but their scope must be described accurately.

The project will distinguish at least the following levels:

1. **AI-generated or AI-assisted implementation:** code or documentation produced or modified with AI assistance.
2. **Human-directed acceptance:** a human decision that a change meets the stated task or acceptance criteria.
3. **Automated verification:** a test, static check, build, or CI job completed with a recorded result.
4. **Manual technical review:** a human inspected the relevant implementation and documented the review scope and findings.
5. **Independent review:** a reviewer who did not author the relevant change evaluated it with sufficient access and independence.
6. **External or operational validation:** evidence from an authorized environment, external custodian, independent participant, or real deployment under a defined protocol.

These levels are not interchangeable. A passing test suite supports only the assertions covered by those tests. A successful build does not prove security, and a human approval does not establish independent review.

### 5.1 Minimum verification record for material changes

For each material code change, the project should retain:

- Pull request and commit references;
- affected components and intended behavior;
- acceptance criteria and known risks;
- relevant test commands and actual outcomes;
- CI run links and commit SHA;
- manual review scope, if performed;
- reviewer identity and independence status, if applicable;
- unresolved findings and explicit non-claims.

Where no independent reviewer is available, record **self-review** or **no independent review**, rather than implying independent approval.

## 6. Research integrity and the v0.6 boundary

The v0.6 preregistration currently states:

- stage: design only;
- claim eligibility: none;
- test data: not generated and not committed;
- confirmatory claims: prohibited;
- independent test custodian: open;
- named approver: open;
- sealed manifest and final freeze: pending.

These controls are central to human accountability. AI-assisted implementation must not be used to bypass the preregistered separation of roles or to imply that a planned study has already produced results.

Before any confirmatory v0.6 execution:

1. Lock the detector, prompt, schema, retry policy, source commit, and analysis plan.
2. Appoint an independent case author/test custodian who does not tune the detector.
3. Keep the test cases and labels unavailable to detector developers before the declared unblinding point.
4. Validate and seal the manifest under the documented protocol.
5. Obtain the named approver's review and record the hashes and roles.
6. Report deviations, missing data, null results, negative results, and failed gates.

AI-generated tests or scenarios may be useful during development, but they must not be represented as independently authored holdout cases if they were produced or inspected by the detector developer or used to tune the system.

## 7. Intellectual property, licensing, and third-party material

The project owner is responsible for checking that submitted and published materials do not infringe third-party rights and that necessary permissions and licenses are respected.

The repository identifies Apache-2.0 licensing for software and CC BY 4.0 licensing for the relevant dataset. These declarations do not automatically establish the provenance or license compatibility of every dependency, code fragment, generated artifact, prompt, or external source.

For material contributions:

- preserve attribution and license notices;
- review dependency licenses and security advisories;
- do not paste proprietary, confidential, personal, or otherwise restricted material into tools without authorization;
- inspect generated code for copied or suspiciously specific third-party content;
- document the provenance of external datasets and references;
- retain the relevant tool/provider terms where they affect use or distribution.

## 8. Disclosure principles for external reviewers and grant applications

The project should describe AI assistance plainly and proportionately. It must not claim that the code was entirely human-written if it was not. It must also not suggest that AI assistance removes the project owner's responsibility.

The public OpenAI Cybersecurity Grant application asks applicants to explain who is involved, the project, methodology, datasets, AI models, dissemination, timeline, and budget. The reviewed form does not ask for a degree or require the applicant to have manually typed the code. The public form and program terms reviewed for this document do not state a blanket prohibition on AI-assisted software development. This observation is **not** a guarantee of eligibility, selection, or acceptance of any particular development process.

The program terms do require attention to third-party rights and permissions and disclosure of related prior research or ongoing projects. OpenAI's general Terms of Use also state that users must not represent model output as human-generated when it was not. The latter is a general service term and should not be misrepresented as a special grant rule.

The program's current priorities and terms can change. Recheck the official pages before making a new submission or material revision.

### 8.1 Suggested disclosure — English

> ARKHÉ is a founder-led project developed through AI-assisted software engineering workflows. The project lead defined the research direction, problem framing, requirements, architectural constraints, acceptance criteria, and evaluation boundaries. AI tools were used to support code implementation and related development tasks. The project lead directed the iterations, evaluated outputs against the stated criteria, and decided which changes to accept or revise. The project lead remains responsible for the project's design decisions, code and dependency provenance, verification strategy, interpretation of results, security claims, and public disclosures. AI-assisted generation and human acceptance are not presented as independent verification. Where external or independent review has not occurred, that limitation is stated explicitly.

### 8.2 Suggested disclosure — Portuguese

> O ARKHÉ é um projeto conduzido por seu idealizador e desenvolvido por meio de fluxos de engenharia de software assistidos por inteligência artificial. O responsável pelo projeto definiu a direção da pesquisa, o problema, os requisitos, as restrições arquiteturais, os critérios de aceitação e os limites de avaliação. Ferramentas de IA foram utilizadas como apoio à implementação do código e a outras atividades de desenvolvimento. O responsável dirigiu as iterações, avaliou os resultados segundo os critérios estabelecidos e decidiu quais alterações seriam aceitas ou revisadas. Ele permanece responsável pelas decisões de projeto, pela procedência do código e das dependências, pela estratégia de verificação, pela interpretação dos resultados, pelas alegações de segurança e pelas divulgações públicas. A geração assistida por IA e a aprovação humana não são apresentadas como verificação independente. Quando uma revisão externa ou independente não tiver ocorrido, essa limitação será declarada explicitamente.

These are draft disclosures. They must be reviewed against the exact tools used, the actual submitted application, and any instructions from the program before being sent externally.

## 9. Actions required to strengthen accountability

| Priority | Action | Completion evidence |
|---|---|---|
| P0 | Review and approve this disclosure as an accurate account of the development process | Project-owner approval recorded in PR |
| P0 | Reconcile the submitted/not-submitted status across continuity, proposal answers, proposal brief, and README | Submission receipt and consistent versioned records |
| P1 | Start an AI-assisted contribution log for future material PRs | Completed log entries with tool/model details when available |
| P1 | Record human review separately from AI generation and automated tests | PR checklist or review record |
| P1 | Review dependency and third-party code provenance | Dependency/license audit and recorded findings |
| P1 | Preserve CI evidence by commit SHA | Linked workflow runs and test summaries |
| P2 | Appoint the independent v0.6 custodian and protocol approver | Named roles and conflict-of-interest declaration |
| P2 | Complete the preregistered freeze before generating or inspecting holdout data | Frozen commit, protocol hash, sealed manifest hash, and approval |

## 10. Contribution log template for future pull requests

Copy this template into a material pull request description or a linked engineering record:

| Field | Entry |
|---|---|
| PR / commit | |
| Date | |
| Tool / provider | |
| Model / version | |
| Task supported by AI | |
| Files or components affected | |
| Human requirements and acceptance criteria | |
| Human decision | Accepted / revised / rejected |
| Automated checks and results | |
| Manual review scope | |
| Independent reviewer | Name or not performed |
| Known limitations / unresolved risks | |

Do not include API keys, credentials, private prompts containing sensitive data, personal data, or confidential third-party content in this log.

## 11. Official references reviewed

Reviewed on 2026-11-16. These references are informational; the live program terms and application instructions prevail if they change.

- [OpenAI Cybersecurity Grant Program application form](https://openai.com/form/cybersecurity-grant-program/)
- [OpenAI Cybersecurity Grant Program terms](https://openai.com/policies/cybersecurity-grant-program-terms/)
- [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/)
- [OpenAI update on the Cybersecurity Grant Program and Trusted Access for Cyber](https://openai.com/index/trusted-access-for-cyber/)

---

## Decision record

**Current status:** Draft for project-owner review.  
**No claim is made** that every historical AI contribution has been inventoried, that all code has received independent review, or that the v0.6 confirmatory study has been executed.  
**Next decision:** approve or correct the factual account, then reconcile the submission-status inconsistency in a separate change.
