# ARKHÉ Commercial Validation Plan

This track is separate from the grant experiment. Benchmark quality does not itself prove that a buyer has a budget, urgency, or deployment path.

## Focused problem statement

Teams deploying tool-using agents cannot reliably reconstruct whether a sequence of individually permitted actions is drifting beyond the original mission. Existing logs show events; they often do not provide a reviewable trajectory linking mission, context, capability, boundary, action, and outcome.

## Initial customer profile

Prioritize one segment for the first ten interviews:

- engineering or security teams operating internal tool-using agents;
- regulated or high-impact workflows;
- existing OpenTelemetry or structured audit logs;
- an identifiable owner for security, platform reliability, or AI governance;
- at least one recent incident, near miss, or blocked production rollout caused by insufficient traceability.

Do not start with “all companies using AI agents.” That is not an actionable market.

## Service-first offer

**Agent Trajectory Risk Assessment — 10 business days**

- Inputs: one bounded workflow, sanitized traces, policy boundaries, and stakeholder interviews.
- Work: map the mission-to-outcome trajectory, identify blind spots, replay agreed scenarios, and quantify alert burden.
- Outputs: evidence map, top five control gaps, prioritized remediation backlog, and a pilot measurement plan.
- Exclusions: continuous production monitoring, autonomous containment, compliance certification, and claims of breach prevention.

This offer tests willingness to pay before investing in a full platform.

## Ten-interview script

1. Describe the last agent workflow you hesitated to deploy or had to constrain.
2. What exact failure were you concerned about?
3. How would you discover that failure today?
4. Which logs or traces would be available after the fact?
5. How long would reconstruction take, and who would do it?
6. What false-alert burden makes a control unusable?
7. Who owns the risk and who controls budget?
8. What evidence is required before production approval?
9. Have you paid for adjacent security, observability, or governance work?
10. Would a fixed-scope assessment be worth running on one workflow? Under what conditions?

Do not pitch until questions 1–9 are answered. Record facts and exact workflow consequences, not compliments.

## Evidence gates

| Gate | Minimum evidence | Decision |
|---|---|---|
| Problem | 6 of 10 interviewees report a recent concrete traceability problem | Continue or narrow ICP |
| Urgency | 3 identify a decision or deadline within 90 days | Build pilot pipeline |
| Buyer | 3 name a budget owner and procurement path | Price the assessment |
| Paid demand | 1 paid assessment or signed paid pilot | Invest in repeatable delivery |
| Product pull | 2 customers request ongoing monitoring after assessment | Evaluate SaaS/MCP product |

## Value metrics

- hours to reconstruct one agent incident;
- percentage of actions linked to a declared mission and policy boundary;
- false alerts per 100 trajectories at an agreed recall floor;
- median lead steps before a boundary violation;
- engineering hours required to add evidence to an approval review;
- number of blocked workflows released after remediation.

## Risks to test explicitly

- Buyers may treat the problem as an existing SIEM/observability feature rather than a new category.
- Synthetic benchmark gains may not survive real workflow diversity.
- Customers may refuse to share traces even after redaction.
- Alerting on near-violations may be valuable for safety but unacceptable for operations.
- Security budget may exist only after a production incident or regulatory requirement.

## Next execution sequence

1. Recruit ten interviewees matching the initial profile.
2. Complete interviews before expanding the product surface.
3. Convert recurring evidence gaps into the fixed assessment template.
4. Price a paid pilot with a narrow workflow and explicit exclusions.
5. Use pilot traces as an independently sourced evaluation set only with written permission and a separate data-governance process.

