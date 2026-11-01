# Document Assistant eval — tuned

Run at 2026-10-31T15:14:46Z · mode `offline` · 37 cases · config `{"chunk_size": 500, "chunk_overlap": 100, "top_k": 4, "min_similarity": 0.1, "store": "memory", "judge_model": null}`

| Metric | Value |
| --- | --- |
| Pass rate | 0.676 |
| Retrieval hit@k | 0.906 |
| Retrieval recall@k | 0.906 |
| MRR | 0.875 |
| PDF page hit | 1.000 |
| Answer accuracy | 0.750 |
| False refusals | 0.031 |
| Refusal accuracy | 0.200 |
| Citation markers valid | — |
| Faithfulness (judge) | — |
| Latency p50 (ms) | 1 |
| Latency p95 (ms) | 1 |
| Cost / question ($) | 0.00000 |

| Category | Pass rate | Cases |
| --- | --- | --- |
| distractor | 60% | 5 |
| factual | 93% | 15 |
| multi_doc | 0% | 2 |
| paraphrase | 57% | 7 |
| pdf | 100% | 3 |
| unanswerable | 20% | 5 |

| Case | Passed | Retrieved | Answer |
| --- | --- | --- | --- |
| leave-01 | ✅ | leave-policy.md, benefits-summary.pdf | # Northwind Labs Leave Policy  Applies to all full-time and part-time employees. Contractors are covered by the Contractor Guide instead.  # |
| leave-02 | ✅ | leave-policy.md, expense-policy.md | Up to 5 unused vacation days can be carried over into the next calendar year. Carried-over days must be used by March 31; any carried-over d |
| leave-03 | ✅ | leave-policy.md, contractor-guide.md | ## Sick leave  Employees receive 10 paid sick days per year. Sick days do not carry over. A doctor's note is required after 3 consecutive si |
| leave-04 | ✅ | leave-policy.md, contractor-guide.md, it-onboarding.md | ## Sick leave  Employees receive 10 paid sick days per year. Sick days do not carry over. A doctor's note is required after 3 consecutive si |
| leave-05 | ❌ | contractor-guide.md, leave-policy.md | ## Time off  Contractors are not eligible for paid vacation, paid sick leave, or parental leave. Planned absences longer than 3 working days |
| leave-06 | ✅ | leave-policy.md, contractor-guide.md | Up to 5 unused vacation days can be carried over into the next calendar year. Carried-over days must be used by March 31; any carried-over d |
| exp-01 | ✅ | expense-policy.md, remote-work.md, leave-policy.md | # Northwind Labs Expense Policy  This policy covers business expenses paid by employees and later reimbursed.  ## Submitting expenses  Submi |
| exp-02 | ❌ |  | The documents do not contain an answer to that question. |
| exp-03 | ❌ | contractor-guide.md | ## Time off  Contractors are not eligible for paid vacation, paid sick leave, or parental leave. Planned absences longer than 3 working days |
| exp-04 | ✅ | expense-policy.md, leave-policy.md, contractor-guide.md | Reimbursements are paid with the next monthly payroll after approval.  ## Approval limits  - Up to $1,000: your manager approves. - $1,000 t |
| exp-05 | ✅ | expense-policy.md, leave-policy.md, remote-work.md, security-policy.md | ## Travel  Book flights through the travel tool. Economy class is required for flights under 6 hours. Premium economy is allowed for flights |
| exp-06 | ✅ | expense-policy.md, remote-work.md, benefits-summary.pdf | ## Home office  New employees can claim a one-time home office stipend of up to $500 for a desk, chair, monitor, or similar equipment. The s |
| sec-01 | ✅ | security-policy.md | # Northwind Labs Information Security Policy  ## Passwords and sign-in  Passwords must be at least 14 characters long. Passwords are changed |
| sec-02 | ✅ | security-policy.md | ## Reporting incidents  Report any suspected security incident, such as a phishing email you clicked or malware on your laptop, to security@ |
| sec-03 | ✅ | security-policy.md, it-onboarding.md, contractor-guide.md | ## Reporting incidents  Report any suspected security incident, such as a phishing email you clicked or malware on your laptop, to security@ |
| sec-04 | ✅ | security-policy.md | ## Data classification  Northwind data has four classes: Public, Internal, Confidential, and Restricted. Restricted data, such as customer p |
| sec-05 | ✅ | security-policy.md, expense-policy.md, it-onboarding.md | # Northwind Labs Information Security Policy  ## Passwords and sign-in  Passwords must be at least 14 characters long. Passwords are changed |
| rem-01 | ✅ | remote-work.md, expense-policy.md, leave-policy.md | # Northwind Labs Remote and Hybrid Work Guidelines  ## Hybrid schedule  Employees assigned to the Bangalore or Berlin office work from the o |
| rem-02 | ✅ | remote-work.md, security-policy.md, it-onboarding.md, expense-policy.md | # Northwind Labs Remote and Hybrid Work Guidelines  ## Hybrid schedule  Employees assigned to the Bangalore or Berlin office work from the o |
| rem-03 | ❌ | leave-policy.md | ## Bereavement leave  Employees receive up to 5 paid days of bereavement leave for the loss of an immediate family member, and 2 days for an |
| rem-04 | ✅ | remote-work.md, benefits-summary.pdf, expense-policy.md | ## Coworking spaces  Employees who live more than 50 km from an office can be reimbursed up to $200 per month for a coworking space membersh |
| it-01 | ✅ | it-onboarding.md, leave-policy.md | # Northwind Labs IT Onboarding Guide  ## Your laptop  New employees choose between a MacBook Pro and a Lenovo ThinkPad X1 Carbon. The laptop |
| it-02 | ✅ | it-onboarding.md | ## Getting help  Ask the IT helpdesk in the #it-help Slack channel. The helpdesk responds within 4 business hours. Urgent issues that stop y |
| it-03 | ✅ | it-onboarding.md, expense-policy.md, security-policy.md | ## Network access  Internal tools are only reachable through the company VPN, which uses WireGuard. The VPN client is installed during lapto |
| con-01 | ✅ | contractor-guide.md, leave-policy.md | ## Time off  Contractors are not eligible for paid vacation, paid sick leave, or parental leave. Planned absences longer than 3 working days |
| con-02 | ❌ | contractor-guide.md, expense-policy.md | # Northwind Labs Contractor Guide  This guide covers independent contractors engaged through a statement of work. Contractors are not employ |
| con-03 | ❌ | expense-policy.md, contractor-guide.md | ## Home office  New employees can claim a one-time home office stipend of up to $500 for a desk, chair, monitor, or similar equipment. The s |
| pdf-01 | ✅ | benefits-summary.pdf, expense-policy.md, it-onboarding.md | Northwind Labs Benefits Summary 2026 - Health Health insurance covers the employee and up to 4 dependents, such as a spouse, partner, or chi |
| pdf-02 | ✅ | benefits-summary.pdf, remote-work.md | Northwind Labs Benefits Summary 2026 - Retirement and Learning Retirement plan: Northwind matches employee contributions up to 6% of base sa |
| pdf-03 | ✅ | benefits-summary.pdf, remote-work.md, leave-policy.md | Northwind Labs Benefits Summary 2026 - Retirement and Learning Retirement plan: Northwind matches employee contributions up to 6% of base sa |
| multi-01 | ❌ | expense-policy.md, remote-work.md, it-onboarding.md | ## Home office  New employees can claim a one-time home office stipend of up to $500 for a desk, chair, monitor, or similar equipment. The s |
| multi-02 | ❌ | contractor-guide.md, leave-policy.md, remote-work.md | # Northwind Labs Contractor Guide  This guide covers independent contractors engaged through a statement of work. Contractors are not employ |
| none-01 | ✅ |  | The documents do not contain an answer to that question. |
| none-02 | ❌ | leave-policy.md | # Northwind Labs Leave Policy  Applies to all full-time and part-time employees. Contractors are covered by the Contractor Guide instead.  # |
| none-03 | ❌ | expense-policy.md, benefits-summary.pdf, leave-policy.md | Reimbursements are paid with the next monthly payroll after approval.  ## Approval limits  - Up to $1,000: your manager approves. - $1,000 t |
| none-04 | ❌ | benefits-summary.pdf, it-onboarding.md | Northwind Labs Benefits Summary 2026 - Retirement and Learning Retirement plan: Northwind matches employee contributions up to 6% of base sa |
| none-05 | ❌ | benefits-summary.pdf | Northwind Labs Benefits Summary 2026 - Health Health insurance covers the employee and up to 4 dependents, such as a spouse, partner, or chi |
