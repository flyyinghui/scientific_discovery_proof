# BootLoops 1.0 — 12 协议 Skills 全文归档

> 来源：`github.com/BootLoops-ai/skills`（commit 196,324 字节 zip，同步于 2026-10-02）。
> 作者：Matthew D. Schwartz（Anthropic《Claude-shaped science》），由 Claude 在其监督下撰写。
> 许可：skill 文本 CC BY 4.0；脚本/插件清单 MIT。
> 本文档为英文原文全文 + 中文导航，供 `scientific-discovery-proof` 技能 Stage 1.5 及后续协议落地查阅。

## 目录

**协议层（7 个通用纪律，任何定量工作都可加载）**

- 验收门 (Acceptance Gate) — 什么算"做完"：绝不靠"拟合过的位数"，必须用独立路线复现 + 正对照 + 双精度稳定
- 常数识别 (Constant Recognition) — 整数关系纪律：先声明候选常数环 + 高度上限，找不到关系就拒绝而非发明
- 植物真值 (Planted Truth) — 合成真值对照先于真实数据；被污染的输入必须被抓到
- 独立性记账 (Independence Bookkeeping) — 参考值的溯源：喂过拟合的 oracle 永远不能认证结果
- 计时纪律 (Timing Discipline) — 先测小规模运行；多小时的投影意味着重构而非扩容
- 阅读契约 (Reading Contract) — 文档阅读工具只能断言"来源里确实有的"
- 工具管理 (Tool Stewardship) — 先查工具库、最后才写代码、为下一个 agent 记录每个工具

**研究层（5 个重型机制，针对特定工作类型）**

- 证明协议 (Prove Protocol) — 用 agent 证明：对抗优先管线、怀疑循环、强制多样性——以及命题本身未知时的理论发现
- 模拟审稿 (Referee Sim) — 外发文档的预审：从它声称的每个受众角度给出最强标准反对意见
- 文献综述 (Lit Review) — 新颖性声明背后的文献审计：全文阅读、可证伪的彻底性、双向引用链
- 参考文献核查 (Ref Check) — 对照权威来源核验书目；民间传说式错误陷阱
- 科学文风检查 (Prose Lint) — 科学散文 linter：炒作词汇、空结构、无 agent 的散文、诚实性与数字核查

---

# 验收门 (Acceptance Gate)

> 职责：什么算"做完"：绝不靠"拟合过的位数"，必须用独立路线复现 + 正对照 + 双精度稳定

---
name: acceptance-gate
description: The standard a computed result must meet before it may be called done. Use whenever an agent claims an integral is solved, a fit has closed, a formula is identified, or any quantitative answer is ready — the claim is not done until it passes this gate.
---

# acceptance-gate — what "done" means

**A result is done when it has survived a check that could have failed, run by
a route that could not have known the answer. It is never done merely because
the computation that produced it finished.**

Why the gate exists: computation produces confident wrong answers at every
stage, and none of them announce themselves. A fit converges to the wrong
basin and reports small residuals. An integer-relation search "recognizes"
numerical noise as a famous constant, because search enough constants and
something always matches a short prefix. Two evaluators built on the same
series expansion agree to great depth on the same wrong value. The agent that
produced the answer — human or model — is the least qualified judge of it,
because everything that produced the answer also produces reasons to believe
it. So "done" is defined externally: agreement with an independent route, at
points that entered no fit, to more digits than the fit could enforce,
deepening when precision is raised, measured by machinery that has
demonstrably failed on a wrong answer. Each clause of that sentence is there
because its absence has, at some point, let a wrong result through.

The bar used for the BootLoops loop-integral results (bootloops.ai): at least
thirty genuine held-back digits, two-precision stable, against an oracle that never fed the fit. Adopt
a bar of that order for anything new. Scale the digit count to the problem;
never scale away the structure.

## The procedure

Run the steps in order. The order is itself part of the discipline: the check
is designed before the answer exists, because a check designed after the
answer exists is chosen — consciously or not — to pass.

**0. Declare the gate before fitting.** Before any fit, search, or model
choice, write down: which evaluation points are reserved, what the
independent route will be, what digit count will count as passing, and what
the controls are. A gate written after the candidate exists inherits the
candidate's blind spots.

**1. Reserve never-fit points.** Choose evaluation points, record them, and
exclude them from every fit, every tuning decision, and every basis
selection — not only the final fit but every exploratory run that shaped the
method. Agreement at fitted points measures interpolation: a fit with enough
parameters reproduces its own inputs exactly, and agreement there means
nothing.

**2. Audit the independent route.** The check values must come from a route
that shares no code, no series representation, and no fitted input with the
derivation. Numerically integrating the original definition, when the
candidate came from a fitted ansatz, is independent; a second wrapper around
the same expansion is not. An oracle whose values entered the fit — even
once, even only to pick a tolerance — is disqualified from certifying (see
independence-bookkeeping). Where full disjointness is impossible, record
exactly what is shared and treat the check as weakened by that much.

**3. Count digits; do not describe them.** Evaluate both sides at the
reserved points and count the digits that genuinely agree. The count must
exceed, by a wide margin, anything the fit's free parameters could have
absorbed. The unit of evidence is a number — "34 digits at each of three
reserved points" — never "excellent agreement".

**4. Rerun at raised precision.** Double the working precision and repeat. A
true identity deepens: the count of agreeing digits grows with the precision.
Agreement pinned at the same depth regardless of working precision is a
truncated intermediate shared by both sides, a coincidence at the resolution
of the search, or a bug. It is never a confirmation.

**5. Run the controls, positive and negative.** Positive: run the identical
gate on a case where the answer is independently known, and confirm it
passes. Negative: perturb the candidate — flip the sign of one term, alter
the last fitted coefficient in its final digit — and confirm the gate fails,
loudly, at the digit where it should. A gate that has never failed anything
certifies nothing: every clause of it might be broken and you would see only
passes.

**6. Leave-one-out, where a fit determined the answer.** For each anchor
point that entered the fit: refit without it, evaluate the refit at the
excluded point, and demand agreement at full depth. An identity survives
every exclusion; an interpolation collapses at exactly the excluded point.
This is the cheapest way to distinguish "found the formula" from "drew a
curve through the data".

**7. Package a standalone evaluator.** The claim ships with a script that
rebuilds the result from the exact data included with it and re-measures this
gate at arbitrary requested precision — no hidden grids, no finite-precision
constants baked in, no state that lived only in the session that produced the
claim. If a stranger cannot rerun the gate, the gate ran once and its
evidence is already decaying.

**8. Report the true verdict.** CLOSED means every part above passed and the
counts are written down. Anything less is OPEN, reported with what was
established and what remains. An honest OPEN is a result; a false CLOSED is
damage, because later work builds on it and the cost of the unwinding grows
with every week it stands.

## Failure modes the gate exists to catch

Each of these is a class observed repeatedly in practice, from agents and
from people. The vignette states the mechanism; learn the shape, not the
example.

- **Satisficing.** The first plausible answer is declared final: a handful of
  digits of numerical noise matches a known constant at the resolution of the
  search, and the search stops. The match was guaranteed by the size of the
  ring searched. The digit bar plus two-precision stability is the cure — a
  coincidence does not deepen.

- **Certifying at fitted points.** The check runs at points the fit saw,
  agreement is perfect, and the perfection is reported as confirmation. It
  confirms only that the fit can reproduce its inputs. Reserved points, set
  aside before fitting, no exceptions.

- **Oracle contamination.** Reference values get used casually during
  development — to pick a tolerance, choose a basis, decide when to stop —
  and are later reused to certify. The gate then verifies that the method
  remembers what it was shown. Track which values touched anything; certify
  only from the disjoint set.

- **False independence through a shared representation.** Two separately
  written evaluators, both resting on the same series expansion or the same
  underlying library, agree to any depth you like — including on a wrong value,
  when the shared layer carries the bug. Their agreement measures the bug's
  consistency. Audit lineage; prefer a route different in kind, not merely in
  authorship.

- **Precision-pinned agreement.** The digit count refuses to grow when
  working precision is raised: both sides share a truncated constant, a fixed
  grid, or a low-precision intermediate. This is the single most diagnostic
  symptom the gate produces. A pinned count is a failure, never "close
  enough".

- **The gate that cannot fail.** The comparison harness itself is broken
  open: a tolerance wide enough to pass anything, a value compared against
  itself through an aliased variable, formatted output string-compared so
  both sides truncate identically, an assertion inside a branch that never
  executes. Every pass from such a gate is vacuous. The negative control is
  the only way to know a gate can fire: you have watched it fire.

- **Threshold drift.** The tolerance is widened, once per awkward case, until
  the candidate passes. The finished gate is then a description of the
  candidate rather than a test of it, and a real error of the same size sails
  through. Thresholds are fixed at step 0 and never touched after the
  candidate exists; a candidate that needs the threshold moved has failed.

- **Adjectives in place of counts.** "Essentially exact", "matches
  beautifully", "agrees to high precision". Every one of these has been used
  to describe agreement that fell apart under an actual digit count. Demand
  the number, the precision it was measured at, and whether the point was
  reserved.

- **Self-graded confidence.** The producing agent's stated confidence offered
  as evidence. Confidence is an output of the same process being audited; it
  tracks fluency, not correctness. The gate is the evidence; there is no
  other kind.

- **Partials rounded up to done.** "Verified" covering nine of ten cases with
  the tenth pending; "closed modulo one term"; a comparison run at lower
  precision than the claim states. The verdict vocabulary is the cure: CLOSED
  has a definition, and the definition is the full gate.

- **The unconditional success line.** A driver prints its PASS banner outside
  the conditional that runs the comparison, or after a caught exception, so a
  run that compared nothing reports success. The verdict line must be printed
  by the comparison itself, from the measured counts — and the negative
  control catches this class too, because a broken driver passes the
  perturbed candidate.

## Two micro-examples

*A fitted closed form.* A candidate formula was fit from evaluations at a
dozen points. The gate: three further points reserved before fitting; the
original definition integrated numerically at those points by a method
sharing nothing with the ansatz; both sides evaluated at two working
precisions and the agreement counted, with the deepening confirmed; one sign
in the candidate flipped and the gate watched to fail at the first affected
digit; each of the twelve anchors dropped in turn and the refit checked at
the dropped point. Only after all of that is the formula an identity rather
than a fit.

*A recognized constant.* A computed number is matched against a declared ring
of constants. The gate: the match must hold to far more digits than the
search consumed; the digit count must grow when the value is recomputed at
higher precision; and the same search, run on noise of the same length, must
come back empty. A search that also identifies noise identifies nothing.

## Checklist before saying "done"

- [ ] Gate declared — reserved points, route, digit bar, controls — before the fit ran.
- [ ] Check route shares no code, no representation, no fitted input with the derivation; any shared remainder is written down.
- [ ] Digit count at reserved points measured and recorded, not adjectivized.
- [ ] Rerun at raised precision; the count deepened.
- [ ] Positive control passed; negative control failed, visibly, at the expected digit.
- [ ] Leave-one-out survived, if a fit determined the answer.
- [ ] Standalone evaluator included: exact data, arbitrary precision, re-measures the gate.
- [ ] Verdict is CLOSED only if every box above is checked; otherwise OPEN, with what remains stated.

**Sources and acknowledgments.** None of the ideas here is new; what is ours is
their assembly into one gate for agent-produced numbers. Declaring the check
before seeing the answer is blind analysis as particle physics practices it
(Klein and Roodman, Annu. Rev. Nucl. Part. Sci. 55 (2005) 141; MacCoun and
Perlmutter, Nature 526 (2015) 187) and preregistration as Nosek, Ebersole,
DeHaven and Mellor argue for it (PNAS 115 (2018) 2600); reserved points and
leave-one-out are Stone's cross-validatory assessment (J. R. Stat. Soc. B 36
(1974) 111); the warning that separately written routes fail together restates
Knight and Leveson's multiversion experiment (IEEE Trans. Softw. Eng. SE-12
(1986) 96).

---

# 常数识别 (Constant Recognition)

> 职责：整数关系纪律：先声明候选常数环 + 高度上限，找不到关系就拒绝而非发明

---
name: constant-recognition
description: Discipline for integer-relation searches (PSLQ, LLL) that turn high-precision digits into exact constants. Use whenever recognizing a numerical value as a closed form, fitting boundary constants, or reporting that no closed form exists.
---

# constant-recognition — naming numbers without fooling yourself

An integer-relation algorithm is a fitting machine. Hand PSLQ a vector of
reals and enough coefficient freedom and it returns a relation, every time;
that is what lattice reduction does. Whether the relation means anything is
decided entirely by choices made **before** the search — which constants are
allowed, how large the integers may be, how many digits pay for it all. The
same choices made *after* seeing the digits are curve fitting with a number
theorist's vocabulary. Everything in this skill exists to keep the decisions
on the correct side of the search.

The asymmetry to internalize: a hit is cheap — noise plus freedom produces
hits on demand — while a null is informative only against a declared ring.
"PSLQ found nothing" means nothing by itself. "Not a Z-linear combination of
{1, ζ(3), π² log 2, Li₃(1/2)} with coefficients below the declared height at
the declared precision" is an exact, reusable, citable statement. The whole
protocol is arranged so that both outcomes mean something.

## The digit budget

Before anything else, the arithmetic that governs the whole exercise. A
candidate relation among n constants with integer coefficients up to height H
consumes roughly n·log₁₀H digits of precision just to be expressible, and a
search run with only that much precision can always satisfy itself. The
digits left over — working precision minus that cost — are the only evidence.
If the surplus is thin, the search is a coin flip; if the ring and heights
cost more digits than you have, the search is theater, and it will still
return a relation. Budget first: choose the ring, choose the largest
coefficients you would believe, compute the cost, and demand a surplus of
many tens of digits before running at all. When the budget does not close,
the correct moves are to compute more digits or to shrink the ring. Running
anyway is the original sin from which every failure below descends.

## Procedure

1. **Declare the ring, in writing, before the first search.** List the
   constants the answer is allowed to draw on and the reason each one is on
   the list: a weight grading, the arithmetic of the geometry the problem
   lives on, the closed forms of solved neighboring cases. The reason
   matters — "it shows up in related problems" admits everything eventually.
   Date the list and keep it with the run, so the record shows the
   declaration preceded the search.

2. **Fix the height bound and pay for it.** State the maximum coefficient
   size you would accept in a believable answer — informed by the heights
   that appear in solved relatives of the problem — then verify the digit
   budget above. Record both numbers with the declaration.

3. **Plant the controls before the real value goes in.** Two of them, both
   pushed through the identical code path — same script, same precision, same
   ring, same height bound:
   - a **positive control**: a value whose closed form in the declared ring
     is independently known. The search must recover exactly that form.
   - a **negative control**: a value constructed to lie outside the ring —
     the digits of a random real at the same precision serve. The search must
     return null.

   A search whose controls have not run is uncalibrated, and any hit it
   produces is unreviewable.

4. **Run, and record everything.** Precision, ring, height bound, the exact
   input vector, the algorithm and its settings. A relation whose search
   parameters were not recorded cannot be distinguished, later, from one
   found by dredging.

5. **Rerun at genuinely higher precision.** Not a handful of extra digits —
   enough to move the noise floor. A true relation persists with the same
   integers; a spurious one dissolves or reshuffles its coefficients.
   Identical integers at two well-separated precisions is the minimum bar for
   taking a hit seriously. It is not the final bar.

6. **Certify on digits the search never touched.** The digits that suggested
   the relation may not also certify it — that is testing a fit on its
   training data. Evaluate the value and the proposed closed form by an
   independent route — a different method or a different implementation — at
   precision beyond everything the search consumed, and demand many digits of
   agreement past the fit. These held-out digits are the acceptance gate;
   nothing moves forward without them.

7. **Report one of two things.** Either the closed form with its full
   certification record (ring, heights, precisions, control outcomes,
   held-out agreement), or the null with its parameters plus the value
   itself: a convergent series or integral representation with an
   arbitrary-precision evaluator, so the number is usable without a name.

## Failure modes

These are the classes the discipline exists to catch. Each one produces
output that looks like success.

**Ring enlargement after seeing the digits.** The declared search fails; a
plausible extra constant goes in "because it appears in related problems";
the enlarged search fails; another constant goes in; the third search closes,
with large coefficients. The closure was manufactured by the enlargement
process — each added constant is added freedom, and enough freedom always
closes. An enlargement is a new experiment: it needs a justification that
does not mention the failed search, and the digit budget must be paid again
for the bigger ring. Repeated ring changes against the same digits are
dredging, whatever the log calls them.

**Height creep.** The same failure on the other axis. The search at the
declared bound returns nothing; the bound is raised "just to see"; a hit
appears. Each raise hands the algorithm more of your digits to spend on
modeling noise, and a relation that appears only after the bound moves is a
statement about the bound. Decide the height you would believe before
searching; a hit above it is grounds for suspicion, never a result.

**The single-precision hit.** A relation found once, at one precision, and
reported. Rerun higher and the integers shuffle — the reduction was returning
the best available fit to that particular noise floor, which is its job. One
precision is zero evidence.

**Stable but correlated: the "recognized" constant that is a fit.** The
subtle one. The relation is stable at two precisions — but both evaluations
came from the same truncated series with a slowly decaying error term, so the
"noise" is the same systematic error twice, and the relation fits that error
as faithfully as it would fit the truth. Two-precision stability tests
against random noise only. The cure is certification from a genuinely
independent evaluation — different representation, different method,
different code — at points never used in the fit.

**Controls bolted on afterward.** The positive control is run after the
discovery, with settings adjusted until it passes, and reported as
calibration. Controls prove the code path only when they run through the
frozen path before the real search; a control tuned after the fact proves
that tuning works.

**The lookup-table shortcut.** Inverse symbolic calculators and large
constant tables are ring enlargement performed by someone else at industrial
scale: they search every constant anyone has cataloged. They are excellent
hypothesis generators and are never results by themselves. A table hit
re-enters this protocol at step 1 — where the declared ring must now answer
the awkward question of why that constant belongs in it.

**Naming under pressure.** Nothing closes and the report is due, so the
"nearest" closed form gets written down, hedged just enough to survive
review. A wrong name is worse than no name: the value works fine as a
number, but a false closed form propagates into later work that trusts it
exactly, and it fails there silently. When nothing closes, refuse. The
refusal deliverable is genuinely useful — the value, the evaluator, the exact
null statement — and a boundary constant with no classical name is sometimes
the interesting discovery. A fabricated name is a corruption of the record.

## A worked shape

What the record of a defensible recognition looks like. The numbers are a
template, not data:

> **Declared** (before search): ring of four weight-graded constants, chosen
> because the solved neighboring cases close at this weight in these
> constants; height bound fixed; digit budget computed from n·log₁₀H; surplus
> large.
> **Controls:** positive (a solved neighbor's value, run blind) recovered
> exactly; negative (random real at working precision) returned null. Same
> script, same settings, before the real value.
> **Search:** hit, with coefficients well under the declared bound.
> **Stability:** identical integers at the working precision and at a second,
> well-separated precision.
> **Certification:** both sides evaluated by an independent method at higher
> precision still; agreement extending far past every digit the search
> consumed.

And the defensible null:

> No relation in the declared ring at the declared height and precision,
> controls passing. Value delivered as a series/integral with an
> arbitrary-precision evaluator; null recorded with its parameters.

Both are results. Only the second is available when the mathematics does not
cooperate, and it has to remain an honorable outcome — otherwise the pressure
to fabricate wins by default.

## Checklist

Before reporting any recognized constant, or any null:

- [ ] Ring declared in writing, dated, before the first search, with a
      stated reason per constant.
- [ ] Height bound fixed in advance; digit budget computed; surplus generous.
- [ ] Positive and negative controls run through the identical code path,
      before the real search, both passing.
- [ ] Search parameters recorded in full.
- [ ] Hit stable — identical integers — under a genuine precision increase.
- [ ] Certification digits independent of every digit the search consumed,
      from an independent evaluation.
- [ ] Any ring enlargement or height raise documented as a new experiment,
      with its own justification and a re-paid budget.
- [ ] If nothing closed: the null stated with its parameters, and the value
      delivered with an evaluator — no invented name.

**Sources and acknowledgments.** PSLQ is the integer-relation algorithm of
Ferguson and Bailey, analyzed and simplified by Ferguson, Bailey and Arno
(Math. Comp. 68 (1999) 351); LLL is the lattice reduction of Lenstra, Lenstra
and Lovász (Math. Ann. 261 (1982) 515). The precision-budget rule, the
two-precision confirmation and the insistence on stating nulls with their
parameters follow the experimental-mathematics practice developed by David H.
Bailey and Jonathan M. Borwein, and by Bailey and Broadhurst for constants
arising in quantum field theory (Math. Comp. 70 (2001) 1719). Most readers will
run these through mpmath (Fredrik Johansson and contributors), PARI/GP or
Mathematica; we are grateful to their maintainers.

---

# 植物真值 (Planted Truth)

> 职责：合成真值对照先于真实数据；被污染的输入必须被抓到

---
name: planted-truth
description: Synthetic-truth controls for analysis pipelines. Use before running any statistical fit, solver, audit, or search on real data — the pipeline must first prove it can recover a known planted answer and catch a deliberately corrupted input.
---

# planted-truth — the pipeline runs on synthetic truth first

**A pipeline that has only ever seen real data has never been tested, because
nobody knew what the right answer was. The only inputs whose correct output
is known are the ones you construct. Construct them, run them, and do it
before real data is touched.**

Real data cannot grade a pipeline. Whatever comes out looks like a finding:
a slope, an evidence ratio, a list of anomalies, an empty list of anomalies.
If the pipeline drops half its input on a parsing error, the output is
smaller and still looks like a finding. If a sign convention is inverted, the
conclusion reverses and still looks like a finding. The one situation in
which output can be graded is when the answer was written down first — a
plant: data generated from known parameters, fed through the full analysis,
with recovery demanded to the accuracy the real analysis will claim.

The order rule is not a nicety. Controls designed after the real output has
been inspected drift toward blessing it: the plant's parameters get chosen in
the region where the pipeline is already known to behave, the corruption
tests get chosen from the failure classes already ruled out, and the
tolerance gets set just wide enough for what was seen. Plant first, look
second. Once real output has been seen, the controls you design are no longer
independent of it.

## The procedure

**0. Freeze the controls before the first real run.** Write down the plants,
the corruptions, the null tests, and the pass criteria for each while the
real data is still unopened. A control invented later, to answer a doubt
about a result already in hand, is evidence of much less.

**1. Recover a plant, through the full path.** Generate data from the model
with known parameters and confirm the pipeline recovers them, to the accuracy
the real analysis will claim. Two hard requirements hide in that sentence.
First, *the full path*: the plant goes through the exact production entry
point, same configuration, same options, same file formats — not a
simplified call that skips the reader, the preprocessor, or the assembly
step, because those are precisely where pipelines break. Second, *the claimed
accuracy*: if the analysis will report an error bar, the planted value must
come back inside it; if it will report evidence for a model, the plant
generated under that model must yield that verdict. Recovery to worse
accuracy than the claim tests a weaker claim than the one being made. Plant
more than once, and include awkward corners of the parameter range along
with the comfortable middle.

**2. Catch corruptions.** Feed the pipeline inputs deliberately broken in
the ways it is supposed to detect — a sign flip, two swapped rows, two
swapped column labels, a block scaled by a constant, a shifted grid, a
duplicated record, a truncated file — one corruption at a time, and confirm
every one is caught, loudly, at the step that claims to catch it. Run a
clean twin alongside: an uncorrupted copy that must pass, proving the alarm
is responding to the corruption and not to everything. A checker that has
never fired is untested; a checker that fires on everything is noise.

**3. Null the machinery.** Where the pipeline sums, averages, or assembles
contributions: push a table of zeros through the full path and demand exactly
the baseline back — not approximately, exactly, because "approximately zero"
is where sign errors and double-counting hide. Re-insert a component the
system already contains and demand its recorded effect back, identically.
Nulls test the plumbing separately from the statistics, and plumbing is where
most real failures live.

**4. Author the fixtures independently of the code under test.** The
expected answer must not come from the pipeline being tested. Generate the
plant by construction — write the answer first, then produce data from it —
or with a separate implementation. An expected-output file regenerated from
the current code turns the test into a check that the code agrees with
itself; every bug present at generation time is baked into the fixture and
certified forever after.

**5. Prove each control can fail.** For every check in the battery, break
its input once on purpose and watch it fire. This is the only way to find
the checks that cannot fail — the aliased comparison, the unreachable
assertion, the tolerance that spans the whole range. A control's first
demonstrated failure is its birth certificate; before that it is a hope.

**6. Record the controls with the result.** The plants, the catches, and the
nulls are part of the deliverable, not scaffolding to delete. A result
whose controls were run but discarded cannot be distinguished, later, from a
result whose controls were never run — and later is when the question gets
asked.

**7. When a control fires on real data: stop.** Diagnose to the root before
any further run. The forbidden move is the plausible benign story — "that
check is oversensitive", "it's probably the known formatting quirk" —
followed by an override. A fired control that gets explained away is worse
than no control: it converts a working alarm into false confidence, and it
trains everyone touching the pipeline to override the next one.

## Failure modes the controls exist to catch

Each is a class seen in practice, in agent-built and human-built pipelines
alike. The vignette states the mechanism.

- **The check that cannot fail.** A comparison of a quantity against itself
  through an aliased variable; an assertion inside a branch nothing reaches;
  a tolerance wider than the range of possible answers. The test suite is
  green from the day it is written to the day the pipeline dies, and it was
  never once capable of turning red. Step 5 is the cure: no check counts
  until it has been watched to fire.

- **The string-compared verifier.** Two numbers formatted through the same
  printer and compared as text: the formatter rounds both sides identically,
  so values differing beyond the printed precision compare equal — and the
  comparison silently tests fewer digits than anyone believes. Worse, when
  both sides pass through the same serializer, a bug in the serializer
  equalizes genuinely different values. Compare numbers as numbers, at a
  stated precision, with the precision printed in the pass message.

- **Fixtures authored by the code under test.** The "expected" file was
  produced by an earlier run of the same pipeline, and gets regenerated
  whenever it drifts. The suite now enforces self-agreement: any bug present
  at fixture time is preserved, and a later fix that changes the output
  reads as a regression. Expected answers come from construction or from an
  independent implementation, never from the thing being graded.

- **The silent-pass leg.** A loop over cases catches exceptions per case and
  moves on; the summary counts the cases that ran. A missing input file
  yields an empty case list, zero failures, and a green banner — "all passed"
  where the denominator was silently zero. Every summary states its
  denominator, and the harness fails when the denominator is smaller than
  declared.

- **The tuned threshold.** A plant is not recovered; instead of finding the
  cause, the tolerance is loosened until it is. Repeat a few times and the
  tolerance is exactly wide enough to pass a broken pipeline — a real error
  of the same size as the widening now passes by construction. A control
  that needs its threshold moved has found something; find out what.

- **The plant designed after peeking.** Real output is inspected first, then
  a synthetic control is built "to confirm" — with parameters, corruption
  types, and pass criteria all chosen in the shadow of what was seen. The
  control confirms; it was never able to do anything else. This is why step
  0 freezes the battery before the real data opens.

- **The simplified-path plant.** The control runs through a convenience
  entry point — smaller grid, mocked reader, the assembly step stubbed out —
  and passes. The real run uses the full path, and the failure lives in a
  step the control skipped. A plant certifies exactly the code path it
  traversed and nothing else.

- **Self-consistency mistaken for a control.** The calculation's own
  convergence diagnostics stay clean orders of magnitude past a real
  failure, because a pipeline that is consistently wrong is still
  consistent. Internal agreement, stability under iterations, and smooth
  residuals are properties of the machinery, not of the answer. Only a check
  with an independent notion of truth counts: a plant, a positivity or
  symmetry constraint the answer must obey, a second route.

- **The explained-away alarm.** A control fires on real data; a plausible
  story is found; the run proceeds. When the failure finally surfaces
  through some other channel, the record shows the alarm worked and was
  overridden — the most expensive possible way to learn the control was
  right. Firing means stop; the story, if true, will survive a root-cause
  diagnosis.

- **The unconditional banner.** The driver prints its completion message
  outside the conditional that checks the results, so a run that verified
  nothing announces success. The verdict text must be produced by the
  verification itself, from measured quantities — and the deliberate break
  of step 5 exposes this class immediately, because the banner also blesses
  the broken run.

## Two micro-examples

*A regression pipeline.* Write down a slope and intercept. Generate data
from them with the noise model the analysis assumes. Run the production
entry point — the same command the real data will get — and demand the
planted values back inside the reported intervals. Then swap two column
labels in a copy of the input and demand the consistency check names the
columns; run the unswapped copy alongside and demand silence. Only then open
the real data.

*An assembler of contributions.* Before trusting a total, push a table of
zeros through the assembly and demand the exact baseline. Then take one
component whose individual effect is already on record, re-insert it alone,
and demand that recorded effect back to the digit. If the zeros come back
nonzero or the known component comes back changed, the plumbing is broken,
and no statistic computed through it means anything.

## Checklist before the first real-data run

- [ ] Control battery — plants, corruptions, nulls, pass criteria — written down before real data was opened.
- [ ] Plant recovered through the full production path, to the accuracy the real analysis will claim, including awkward parameter corners.
- [ ] Every claimed detector shown to catch its corruption, loudly; clean twin passed alongside.
- [ ] Zeros through the assembly returned the exact baseline; a known component returned its recorded effect identically.
- [ ] No fixture was authored by the code under test.
- [ ] Every control has been watched to fail at least once, on a deliberate break.
- [ ] Pass messages state counts and denominators; no banner prints outside the verification.
- [ ] Controls filed with the result, not deleted.
- [ ] Standing order acknowledged: a control that fires on real data stops the run until the root cause is known.

**Sources and acknowledgments.** Planted-truth recovery is what statisticians
call simulation-based calibration (Cook, Gelman and Rubin, J. Comput. Graph.
Stat. 15 (2006) 675; Talts, Betancourt, Simpson, Vehtari and Gelman,
arXiv:1804.06788) and what experimental collaborations call injection tests or
mock-data challenges; "prove each control can fail" is mutation testing
(DeMillo, Lipton and Sayward, IEEE Computer 11(4) (1978) 34); positive and
negative controls are borrowed, name and all, from the wet lab. We claim only
the checklist.

---

# 独立性记账 (Independence Bookkeeping)

> 职责：参考值的溯源：喂过拟合的 oracle 永远不能认证结果

---
name: independence-bookkeeping
description: Provenance rules that keep checks independent. Use when setting up any comparison, oracle, or reference value — and whenever tempted to certify a result with machinery that helped produce it.
---

# independence-bookkeeping — keeping the second route honest

**THE LAW: independence is an auditable property of records, never an
assumption. Two routes are independent when you can produce the trail showing
what each one depends on — code, inputs, tuning history — and the trails do
not meet at any layer where the feared error could live. If you cannot produce
the trail, you do not have independence; you have a feeling, and correlated
routes agree wrongly with exactly the same warm feeling as independent ones.**

The strongest evidence a computed result can carry is agreement with a second
route that could not have failed the same way. The entire content of that
check is the "could not" — and the "could not" is a fact about records, not
about intentions. Nobody sets out to build a circular check. Independence
decays silently, through ordinary tidy-minded acts: a stale reference gets
"refreshed" with the current code; two evaluators quietly converge on the
same library; an oracle's values leak into the tuning of the thing the oracle
later certifies. None of these announce themselves, and every one of them
leaves the comparison script printing PASS. The only defense is bookkeeping
kept from the start, because independence lost cannot be reconstructed
afterward — once a value has touched a fit, no amount of later diligence
untouches it.

## The one-way contamination rule

**An oracle that fed a fit may never certify the result.** Contamination is
one-way and permanent. The moment a reference value influences any choice —
a fitted parameter, a model form, a tolerance, a stopping decision, even
which of several candidates you kept — that value belongs to the production
side of the ledger forever. Certification draws only from the disjoint set:
values the fitting process never saw and could not have seen.

This is stricter than it first looks. Influence includes the soft channels:
you glanced at the reference while debugging and "fixed" the code until it
agreed; you used it to decide how many terms were enough; you discarded a run
because it disagreed with it. All of these are fits in everything but name.
The test is counterfactual: **if this reference had been different, could
anything about the result have come out different?** If yes, it fed the fit.

## The ledger — what to write down and when

Keep provenance as an append-only record, written at the moment of creation,
not reconstructed at certification time. Memory of provenance is worthless;
the whole point is that six weeks later nobody remembers which script
produced the number.

**1. A birth record for every reference value.** Generator (program plus
version or commit), inputs and settings, working precision, the estimated
accuracy *and where that estimate comes from* (internal convergence, an
error bound, agreement with something else — name it), and the date. A
reference without a recorded accuracy cannot support a digit claim: a
comparison is only as good as the weaker side, and an undocumented reference
has no known strength. Comparisons have stalled at exactly the digit count
of a reference nobody recorded — the agreement was real, and every claimed
digit past it was manufactured.

**2. A contact log for every oracle.** Each time a value enters a fit,
a tuning decision, a model selection, or a debugging session, append the
event. The log is append-only; entries are never removed, because the rule
above is one-way. Certification of claim C requires a reference whose
contact log contains neither C nor anything C was built on.

**3. A lineage audit for any claimed "two independent routes."** Walk each
route's dependency stack down to the libraries, the tabulated inputs, and
the constants. Two programs in different languages that call the same
special-function library share that library's defects; two derivations that
read the same published table share its typos. Shared hardware and compilers
rarely matter; shared mathematics and shared data almost always do. Write
down the *deepest shared layer* and then argue, in writing, that the failure
you are guarding against cannot live there. "Fully disjoint" is often
impossible — that is fine; undocumented sharing is what kills you, not
sharing itself.

**4. One deliberately different engine.** Keep an evaluator around precisely
because it shares nothing with the rest of your stack — different algorithm,
different language, different author if you can get one. It will be slower.
Its value is not speed; its value is that its errors are uncorrelated with
everyone else's, which makes its agreement worth more per digit than any
in-family check.

**5. The comparison itself is code — test it before believing it.** Before
any pass counts as evidence, feed the comparator a deliberately mismatched
pair and watch it fail. A comparator that has never been seen to fail proves
nothing: loose tolerances, a wrong column, a string comparison of truncated
prints — all of these return agreement on everything, forever, and the
output looks identical to a real pass. Also write down, *before* running the
real comparison, what outcome would count as failure. A failure criterion
chosen after seeing the numbers is a fit.

**6. Close the loop in the record.** When a comparison certifies a claim,
the certificate cites the reference's birth record; the reference's contact
log gains the claim. The reference is now burned for anything built on top
of that claim. This is the price of using it, and the ledger is how you know
the price was paid.

## Failure-mode catalogue

The classes this discipline exists to catch. Every one of them prints PASS.

- **The shared-library twins.** Two "independent" implementations both call
  the same underlying expansion; a defect there makes them agree, wrongly,
  to full precision — the check measures the library's self-consistency.
- **The regenerated reference.** A stored reference goes stale or missing
  and someone helpfully re-derives it with the current code; from that day
  the check compares the program with itself and can never fail again.
- **Circular calibration.** Route A is tuned until it matches route B; route
  B is later "validated" by its agreement with route A. Each certificate
  cites the other; nothing external anchors either one.
- **The leaky oracle.** Reference values were used to choose among candidate
  models — keep the form that matches — and then the same references certify
  the chosen model; the certificate measures the selection, not the truth.
- **The undocumented-precision stall.** The comparison "confirms to many
  digits", but the reference was only ever good to fewer, a fact recorded
  nowhere; every digit past the reference's true accuracy is fiction.
- **Contamination one step removed.** The raw values are properly held out,
  but the "independent" check compares residuals computed with the fitted
  parameters — the held-out quantity is a function of the fit.
- **The comparator that cannot fail.** Tolerance too loose, wrong field
  compared, truncated strings matched — the harness agrees with anything,
  and nobody ever planted a known mismatch to find out.
- **The helpful cache.** A shared cache or memoization layer serves route B
  the value route A stored; two routes return the same number because it is
  the same number.
- **The convenient partial audit.** Independence declared after inspecting
  the top layer only; three layers down, both routes read the same input
  table.
- **Post-hoc promotion.** A value computed as a quick internal cross-check
  is promoted months later into the official certificate, its casual birth
  record never upgraded to match its new weight.

## Worked micro-example: certifying a fitted constant

You fit a linear combination of candidate constants to a high-precision
value and the fit closes beautifully. What certifies it?

*Not* agreement with the value you fit to — that is residual arithmetic
restated, evidence of nothing. Certification needs digits the fit never saw:
extend the target value past the precision used in the fit, using an
evaluator that did not produce the fit input, and check the fitted form
against the extension; or evaluate both sides at a different point where an
untouched reference exists. Add the destructive control: refit with one
supposedly essential candidate removed and confirm the fit collapses. A fit
that survives the removal of its key ingredient was never measuring that
ingredient.

A birth record small enough that there is no excuse to skip it:

```
value:     target integral at the check point
accuracy:  60 digits (internal convergence estimate; last 5 digits unconfirmed)
generator: series evaluator v3.2 (commit <hash>), 80-digit working precision
date:      <date written at creation>
contacts:  fed the ansatz fit of <date>  -> may not certify that fit
```

Five lines. The last one is the ledger doing its job: whoever reaches for
this value at certification time is told, by the record and not by memory,
that it is burned.

## Closing checklist

Before calling any agreement a certification:

- [ ] Every reference has a birth record: generator + version, inputs,
      accuracy with its basis, date — written at creation, not recalled.
- [ ] Every oracle has a contact log; every fit, tuning, selection, and
      debugging use is in it.
- [ ] The certifying reference is disjoint from the claim: not in its
      contact history, not produced by the code under test.
- [ ] The counterfactual test passes: had the reference differed, the
      result could not have come out different.
- [ ] For "two independent routes": the deepest shared layer is named in
      writing, with the argument that the feared error cannot live there.
- [ ] The comparator has been shown to FAIL on a planted mismatch.
- [ ] The failure criterion was written down before the comparison ran.
- [ ] Claimed agreement digits do not exceed the recorded accuracy of the
      weaker side.
- [ ] The certificate cites the birth record; the contact log now records
      the certification, burning the reference for anything built on it.

If any box is unchecked, the honest statement is "consistent, pending an
independent check" — and the word *independent* stays out of the writeup
until the ledger can back it.

The empirical basis for distrusting "independent" implementations that share a
layer is Knight and Leveson (IEEE Trans. Softw. Eng. SE-12 (1986) 96); the
one-way contamination rule is the train/test separation of statistical learning
stated for oracles.

---

# 计时纪律 (Timing Discipline)

> 职责：先测小规模运行；多小时的投影意味着重构而非扩容

---
name: timing-discipline
description: Compute-planning rules. Use before launching any calculation whose runtime is not already measured — and whenever an agent proposes a long run, an overnight grind, or a bigger machine as the way forward.
---

# timing-discipline — measure first, restructure early

The expensive mistake in computational work is rarely the wrong algorithm. It
is the run that consumes a night, a weekend, or a machine-week and returns
something a ten-minute pilot would have predicted. Runtime intuition is
systematically optimistic — in people, and worse in language models, which
produce fluent, confident durations for jobs they have never timed, because
plausible-sounding ETAs are easy to generate and nothing in the generation
process consults a clock. Hence the founding rule:

**An estimate not derived from a measurement of this calculation, in this
configuration, on this machine, is a guess.** Every projection is either
(a) fit from the job's own time-stamped log, (b) taken from a measured prior
run of identical configuration on the same hardware, or (c) reported as
"unknown — measuring now." There is no fourth category.

The second rule is what to do with the measurement. When a projection comes
out long — past a couple of hours — the right response is almost never a
bigger run, a bigger machine, or an overnight slot. It is restructuring the
problem so the run shrinks. Measured honestly, most long projections are the
computation telling you that you are solving it the wrong way.

## Procedure

1. **Pilot before anything that might be long.** Same code, same machine,
   same settings, same distribution of cases — scaled down in size only, with
   a time-stamped log. If the job cannot be scaled down, that is itself a
   design defect worth fixing before launch, because it also means the job
   cannot be checkpointed or partially salvaged.

2. **Fit the rate from the steady-state window.** Discard the startup
   transient: the first items carry compilation, cache fill, and input
   loading, and a rate fit across them is wrong in whichever direction hurts
   more. Then check the per-item cost trend across the pilot. If cost grows
   with index — swelling expressions, accumulating state, rising memory — a
   linear extrapolation is a floor, not a forecast: run the pilot at two
   sizes and fit the growth exponent instead.

3. **Write the projection down with its provenance** before launching: pilot
   size, window used, measured rate, scaling assumption. A projection whose
   provenance cannot be stated in one line is an estimate wearing a number.

4. **Apply the threshold.** If the projection exceeds a couple of hours,
   stop. Do not launch, do not reach for more cores. Restructure instead, and
   actually enumerate the candidates: a better representation or basis; an
   exact reduction that shrinks the object before any numerics touch it; a
   symmetry that collapses the case count; a split into independent pieces; a
   cheap method for the bulk of the cases with the expensive one reserved for
   the residue; a limit or special case that answers the actual question
   without the general computation. The restructured route usually exists,
   and when it exists it beats hardware by more than hardware can give.

5. **Fresh eyes before any long run.** Before committing to a projection near
   or over the threshold, have someone — or a separately prompted agent with
   no stake in the current plan — spend a short, bounded effort on one
   question: is there a structurally smarter route? Record the verdict either
   way. "Current route is right because X" is a valid outcome; silence is
   not, because the absence of a recorded verdict is indistinguishable from
   the question never having been asked.

6. **Define real progress before launch.** Name the output unit the run
   exists to produce and the file or table where it accumulates. Monitoring
   watches that count. Log volume, CPU load, and process liveness are not
   progress; they are signs of activity, and activity is what a stuck job
   emits too.

7. **A rate collapse voids the projection.** If the measured rate drops
   severalfold mid-run, stop quoting the old ETA that instant. Diagnose,
   re-measure, re-plan. A projection is conditional on the rate it was fit
   from; when the rate goes, the projection is gone with it.

8. **Re-measure on any change.** New machine, new input regime, new working
   precision, new parameter range: the old rate does not transfer, however
   similar the job looks. Rates are properties of a configuration, not of an
   algorithm.

## Failure modes

Each of these has burned real time. Each looks reasonable from the inside
while it is happening.

**The unmeasured overnight launch.** A job goes up at the end of the day
because the day is ending, on the theory that the night is free anyway.
Morning finds it a small fraction done, dead, or wedged — and the night was
not free: it cost the diagnosis time, the cleanup, and a day of schedule
built on the assumption it would finish. The launch decision was made by the
calendar, not by a measurement.

**The intuition ETA.** "About an hour, probably." From a person this is
optimism; from a model it is fluent confabulation with the grammar of a
measurement. The tell is that no log exists from which the number could have
been derived. The question that kills it is three words: measured from what?

**The startup-transient fit.** A rate fit from the first items either
includes one-time warm-up costs — projecting the run as far grimmer than it
is, so a feasible job gets canceled — or is taken after caches are warm and
omits a cost the full run pays over and over. Both are cured by fitting the
steady-state window and saying which window was used.

**Linear extrapolation of a superlinear cost.** Every item slightly costlier
than the last: growing intermediate expressions, an accumulating store,
memory pressure building toward swap. The pilot's rate is the best rate the
run will ever see, the projection is a lower bound presented as a forecast,
and the wall arrives hours after the promised finish. The two-size pilot with
a fitted exponent exists for exactly this.

**Grinding past the rethink.** The most expensive class in the catalog. A
route measured to be long gets ground through anyway, because grinding feels
like progress and rethinking feels like starting over. A day goes into
babysitting the run — restarts, memory tweaks, partial salvage — while a
reformulation that would remove most of the work sits unexamined. When the
reformulation is finally tried, it finishes before the grind would have. The
threshold rule exists to force this comparison while it is still cheap.

**The bigger-machine reflex.** The projection is bad, so the plan becomes
more cores. Parallelism pays at most the width factor, and only when the
problem splits cleanly; a restructure removes the work itself, which no
amount of width can do. Hardware comes after the structure is right, not
instead of it.

**The rate collapse ignored.** Mid-run the rate drops severalfold — the hard
cases arrive, memory tightens, another job lands on the same machine — but
the original ETA keeps being quoted because it is written down and quoting it
is easier than re-measuring. Every "almost done" derived from the dead rate
is fiction, and every plan built on it inherits the fiction.

**Log lines mistaken for progress.** The job prints steadily, therefore it is
working — except the printing is a heartbeat, a retry loop, or a progress
indicator over a phase that finished long ago, and the output file has not
grown in hours. Liveness is measured on the output class the run exists to
produce; everything else is the sound of a fan.

**Sunk-cost continuation.** "It has been running too long to kill now." The
hours already spent are not an argument for spending the rest; they are
spent either way. The only live comparison is the measured remaining time of
this run against the total time of the restructured route — and the
restructured route often wins even starting from zero.

**The unfaithful pilot.** The pilot ran with different flags, lower
precision, warm caches, or the easy slice of the input, so the projection
describes a different computation. The sharpest variant: case difficulty
grows with index, and the pilot sampled the easy head of the list. The pilot
is the run, scaled down, with nothing else changed — and drawn from the same
distribution of cases as the real thing.

## The worked shape

The whole discipline in symbols. The pilot's steady-state window yields n
items in time t, so the rate is r = n/t. The full run has N items, so the
projection is N/r — under an explicitly stated linearity assumption. If two
pilot sizes disagree with that assumption, fit cost ∝ N^α and project with
the fitted α, saying so. Then the branch: projection under the threshold —
launch, with the progress unit defined and a standing rule that a rate
collapse voids the ETA; projection over the threshold — restructure first,
with the fresh-eyes verdict recorded before any long launch is even
considered.

The same shape covers monitoring. Before launch, write down: progress is the
row count of the results file, expected to grow at roughly r. During the run,
the check is that count against that expectation — never "the log is still
scrolling," and never "the process is still alive."

## Checklist

Before launching anything that might be long:

- [ ] Pilot run: same code, machine, settings, and case distribution;
      time-stamped log kept.
- [ ] Rate fit from the steady-state window; per-item cost trend checked;
      scaling assumption stated.
- [ ] Projection written down with one-line provenance before launch.
- [ ] Projection over the threshold? Restructuring candidates enumerated and
      tried, and a fresh-eyes verdict recorded, before any long launch.
- [ ] Real-progress unit defined, with where it accumulates and the expected
      rate; monitoring watches it, not the log.
- [ ] Standing rule armed: a severalfold rate drop voids the ETA and triggers
      a re-plan, not a wait.
- [ ] Any change of machine, input regime, or precision → re-measure before
      re-projecting.

---

# 阅读契约 (Reading Contract)

> 职责：文档阅读工具只能断言"来源里确实有的"

---
name: reading-contract
description: Sources-only discipline for any instrument or agent that reads documents and asserts facts from them — literature audits, record replays, data extraction, citation of prior work.
---

# reading-contract — assert only what the record supports

**THE CONTRACT: an instrument that reads documents asserts only what the
record in front of it supports, with the citation attached at the level of
page, table, equation, or line. Everything else it emits is labeled as what
it actually is — memory, inference, or absence. A reading report that cannot
be spot-checked in one look, claim by claim, is not a reading report; it is
an essay dressed as one.**

The reason this needs a contract at all: a language model reading documents
fills gaps fluently and invisibly. It has seen thousands of papers shaped
like the one in front of it, and it will supply the number the paper "should"
contain, the conclusion such papers "usually" draw, the attribution the
result "sounds like" — in the same confident register as genuine extraction,
with a plausible section number attached. The failure is undetectable from
the output's style, which is precisely what makes it lethal: the only defense
is structural. Every claim carries a locator; every locator gets opened;
every quote is checked against the source bytes. Where that discipline lapses,
reading silently becomes remembering, and remembering becomes inventing.

## The procedure

**1. Open the actual record.** "Read" means the source bytes are in front of
the instrument in this session — not a recollection of the title, not a
secondary account, not an abstract standing in for the body. If the source
cannot be opened, the honest output is "not checked," stated as such. An
answer from memory dressed in a citation is worse than no answer, because it
poisons every later check that trusts the citation.

**2. Extract with locators.** Every asserted fact carries its source plus a
locator precise enough that a checker lands on the sentence: page, table row,
equation number, figure panel. A claim you cannot point to is not extracted
yet — go back and find it, or downgrade it to a labeled inference. Record
which version of the source the locator refers to (preprint versus published;
edition; revision date): locators rot when versions shift, and a broken
locator quietly breaks the entire audit trail behind it.

**3. Quote before paraphrase for load-bearing claims.** When an assertion
will carry weight in later work, carry the verbatim sentence next to the
paraphrase, copied from the source text — never re-typed from memory, which
is where drift enters. The check on the claim is then one look instead of a
search. Quotation marks are a legal instrument: they promise the string
occurs literally in the source. A fair paraphrase inside quotation marks is
a fabrication, however faithful its content.

**4. Preserve the hedge at source strength.** "Consistent with" is not
"confirms"; "suggests" is not "shows"; a conjecture in the source stays a
conjecture in your note. The modal is part of the claim. Restatements are
checked against the carried quote, never against the previous restatement —
chains of summaries strengthen monotonically, one fair-sounding notch at a
time, until the source is credited with a result it explicitly declined to
claim.

**5. Classify outcomes honestly.** When checking a published value against
its own stated inputs, there are exactly four honest outcomes: it
*reproduces*; it is *determined only under conventions the record does not
state* (name the assumed convention); it is *undetermined* by what the record
provides; or it is *uncheckable* with what you have. "Probably meant" is not
an outcome. A mismatch you can erase by guessing a normalization is not a
reproduction — it is the second category, reported as the second category.

**6. Scope every attribution.** A claim belongs to the sentence's actual
author at the sentence's actual strength. One paper is not the field; the
boldest sentence in one introduction is not a consensus. "It is known that"
requires either a source that says so or deletion. Absence claims scope to
the search performed: "these records do not state X" is assertable after
actually searching them; "the literature contains no X" is a claim about a
search you must be able to describe.

**7. Type retrieval as retrieval.** A result found in a source during
reading is recorded as retrieved, with the source — never re-presented as
something derived here. This holds even when you could have derived it: the
provenance of *how you actually got it* is the fact being recorded. A value
copied from a table and later "independently confirmed" against that same
table is a copy agreeing with itself. Never claim independent derivation of
a published result.

**8. Verify bibliographic identity.** Authors, title, venue, year,
identifier — checked against the canonical databases before the entry is
cited, not copied from a previous citer. Folklore errors propagate precisely
because each citer trusts the one before; the chain breaks only where
someone opens the record.

**9. Separate the layers in the report.** Three bins, visibly labeled:
*read* (facts with locators, quotes verified); *inferred* (labeled, resting
on named read facts); *background* (memory, unverified — quarantined, and
either verified against a source before use or excluded from anything that
carries weight). A report that mixes the bins forces every reader to re-do
the reading to find out which sentences are load-bearing.

## Failure-mode catalogue

The classes this contract exists to catch. Each reads fluently; none survives
opening the source.

- **Memory dressed as reading.** The report cites a section for a claim the
  instrument pulled from its recollection of similar papers; the section,
  opened, says something narrower, later, or nothing of the kind.
- **Paraphrase drift.** Each restatement strengthens the hedge one notch —
  consistent-with becomes finds becomes establishes — and the final summary
  credits the source with a claim it explicitly avoided.
- **The phantom quote.** Quotation marks around a fair-sounding paraphrase;
  the string occurs nowhere in the source, and the marks convert a summary
  into manufactured evidence.
- **Abstract-for-body citation.** The abstract's headline is cited for a
  quantitative claim that lives only in the body, under assumptions the
  abstract omits — or that appears nowhere in the paper at all.
- **One-paper-to-field promotion.** A single group's statement becomes "the
  field believes"; a second source would refute the consensus being invented.
- **Secondary-source laundering.** A review's summary of a paper is
  extracted and cited as the paper itself; the review's simplification now
  travels with the original's authority.
- **Convention smuggling.** A published value "fails to reproduce" because
  the reader silently assumed a normalization or sign convention the record
  never states — the honest outcome was "determined only under unstated
  conventions," not "wrong."
- **Locator rot.** The claim is genuine but the pointer is to a different
  version — equations renumbered between preprint and journal — so every
  later checker fails to verify and the trail dies silently.
- **Negative claim without a search.** "Not addressed in the literature"
  asserted after reading three papers; the claim's true scope was those
  three papers and the one query that found them.
- **Retrieval passed as derivation.** A value found in a table during the
  reading pass is later presented as computed here, and its "independent
  confirmation" is its own reference.
- **Version skew.** A claim read in the preprint is attributed to the
  published version, and the two differ at exactly the sentence in question.
- **Bibliography folklore.** Year, author list, or venue copied from a
  previous citer's error and propagated, because nobody in the chain ever
  opened the canonical record.

## Worked micro-example: the drift chain

Source sentence: *"our results are consistent with a vanishing correction."*

- Note, first pass: "they find the correction consistent with zero." — fair.
- Second pass, summarizing the note: "they find no correction." — a claim
  the authors did not make.
- Third pass, citing the summary: "it is known that the correction
  vanishes." — folklore, three steps from birth, each step a fair-sounding
  summary of the one before.

Only the first restatement is a fair summary *of the source*. The cure is
mechanical, not moral: the verbatim quote travels with the claim, and every
restatement is checked against the quote. The chain cannot drift when every
link is forged against the same original.

## Worked micro-example: the extraction record

The format that makes spot-checking one look instead of an afternoon:

```
CLAIM:    the second-order coefficient is given in closed form
SOURCE:   [Author, Year], published version, Eq. (3.12), p. 9
VERBATIM: "the coefficient at second order reduces to [expression]"
          (copied from the source text, not re-typed)
STATUS:   read — quote verified against source
```

and, kept visibly apart from it:

```
BACKGROUND (memory, unverified): expansions of this type typically
converge inside the unit disk. Not asserted; verify before use.
```

The second block is not a weakness in the report — it is the report being
honest about which of its sentences were read and which were remembered. The
failure is not having background knowledge; the failure is letting it wear
a locator.

## Closing checklist

Before a reading report ships:

- [ ] Every asserted fact carries source plus locator (page / table /
      equation / line), with the source version identified.
- [ ] Every locator was verified by opening the record in this session —
      none inherited from memory or a previous citer.
- [ ] Load-bearing claims carry verbatim quotes copied from the source
      bytes; every quotation-marked string literally occurs in the source.
- [ ] Hedges preserved at source strength; restatements checked against
      the quote, not against earlier restatements.
- [ ] Every check outcome is one of: reproduces / determined only under
      unstated conventions / undetermined / uncheckable — no "probably
      meant."
- [ ] Attributions scoped to the actual author and paper; no one-paper
      claims promoted to the field.
- [ ] Abstracts cited only for what the abstract itself supports.
- [ ] Negative claims scoped to the records actually searched, with the
      search describable.
- [ ] Everything retrieved is typed as retrieval; no found result is
      presented as derived here.
- [ ] Read / inferred / background layers visibly separated; background is
      quarantined from anything that carries weight.
- [ ] Bibliographic identity of every cited entry checked against a
      canonical database, not a previous citer.

The test of the whole report: hand it to a skeptic with the sources open.
If any sentence sends them searching rather than looking, the contract was
not met for that sentence.

---

# 工具管理 (Tool Stewardship)

> 职责：先查工具库、最后才写代码、为下一个 agent 记录每个工具

---
name: tool-stewardship
description: How the toolkit is consulted, extended, and documented. Use before writing any new code — and after, when a genuinely new instrument has earned its place.
---

# tool-stewardship — consult first, write last, document always

A research program in which agents do much of the work accumulates capability only if someone makes it accumulate. Code gets written constantly; the question is whether the tenth problem starts where the ninth finished or starts from zero. Left to defaults it starts from zero: each session writes a script, solves its problem, and exits, and everything the script learned leaves with the context that held it. A shared toolkit converts that loss into compounding — but only under habits that do not happen on their own: consult before writing, improve in place rather than copy, document the day you build, retire what has been superseded. This file is those habits as procedure.

The economics are lopsided. Consulting an index costs minutes; rebuilding an instrument costs hours, and the rebuild is usually worse, because the existing tool embodies fixes for failures its author already hit and a fresh script embodies none. A tool that has survived many problems carries their corrections; new code carries only its author's foresight. The same asymmetry is why patching beats forking: a fork stops inheriting the moment it is copied, so every later correction to the original must be rediscovered in the fork, usually by getting a wrong answer first. And documentation is same-day work because the author is the only person who knows what the tool assumes, and only briefly. A page written a week later records the memory of an intention; a page written the day of the build records the fact of a behavior.

## Procedure

### Before writing any code

1. **Search the index by capability, not by name.** You are looking for "something that fits a rate to a time-stamped log," not for a title you half-remember. Read past the one-line summaries: a near-miss matters, because a near-miss plus a patch is the usual right answer.
2. **Read the candidate's page in full.** The page says when the tool applies and what test its output must pass. Skimming the page and then "verifying" by eyeballing one output is how the wrong tool gets trusted.
3. **Run it on a trivial case with a known answer** before running it on your problem. This costs a minute and catches both your misreading of the interface and any rot in the tool itself.
4. **Climb the decision ladder in order:** use as-is → patch or extend → wrap → write new. Writing new code obliges you to state, in one written sentence, which existing tools you checked and why each falls short. If you cannot write that sentence, you have not consulted; go back to step 1.

### When patching an existing tool

1. **Patch the upstream copy, in place.** Never a private copy in your working directory — the point is that the next user inherits the fix.
2. **Preserve the interface, or migrate every caller in the same change.** Search for the call sites first. A changed output format with an unmigrated caller produces wrong numbers that still parse (see the catalogue).
3. **Re-run the tool's known-answer tests, plus the case that motivated the patch.** Then add the motivating case to the tests — it is the one input class the tests demonstrably lacked.
4. **Log the change the same day**: date, what changed, why, and what a user of yesterday's version would see differently. The log lives where the next user will look, and the tool's page is updated whenever the meaning of the output moved. An undocumented upgrade is indistinguishable from a regression.

### When new code is justified

1. **Prove it on known answers before the real problem.** New code earns trust the way a new instrument does: by getting right the cases where right is checkable.
2. **Decide, honestly, whether it outlives the problem.** If yes: name it, move it into the toolkit tree rather than leaving it beside the run that spawned it, write the four-question page below, and add the index row — all the day it is built, because tomorrow you will be inside the next problem and the day after you will not remember the preconditions.
3. **If it is genuinely one-shot, say so in a comment at the top of the file**, so a later reader knows it was left unregistered on purpose. Be suspicious of that verdict, though: "one-shot" is usually a failure to imagine the next problem, and the catalogue below is full of one-shot scripts that got rebuilt monthly.

### The four-question page

Every tool's page answers four questions for a reader who has never seen the tool:

1. **What it does** — one plain paragraph.
2. **When to reach for it** — the symptom or task that should route here, and the neighboring tool that covers the adjacent case, so the reader can see the boundary.
3. **What its output means** — units, conventions, and what failure looks like as distinct from success. A tool whose failure output resembles its success output needs that fact stated in bold.
4. **What test its answer must pass before anyone believes it** — the known-answer case, the cross-check against an independent route, whatever the acceptance criterion is.

A tool missing any of the four is not finished, however well it runs. Example of a complete entry:

```
## ratefit — runtime projection from a partial log
Fits a rate to a job's own time-stamped log and projects completion.
When to reach for it: before extending any running job, or when
deciding whether a projected run fits a time budget. Not for jobs
whose per-item cost grows with the item index — no tool covers
those yet; measure directly.
Output: projected finish time plus a fit residual. A residual above
the printed threshold means the rate is unstable and the projection
is VOID, not merely approximate.
Believe it when: the projection from the first half of a finished
job's log matches that job's actual finish.
```

A reader of that block can decide whether to use the tool, use it, and distrust it correctly — without opening the source.

### Retiring duplicates

When two tools overlap, merge into the stronger one and port whatever cases only the weaker handled; the weaker tool's tests are the checklist for the port. Then delete the loser and leave a one-line pointer at its old name and its old index row ("superseded by X, date"), because habits and links keep pointing at dead names for months. Never leave both live "for safety" — every future reader then re-litigates the choice, and some choose wrong.

## Failure-mode catalogue

These are the classes the discipline exists to prevent. Each recurs wherever the procedure is skipped.

- **Parallel half-tools.** Two sessions each need most of the same instrument and each writes its own; each handles the failure cases its own problem hit, and neither inherits the other's. Result: two tools, each incomplete in a different way, with disjoint bugs — and every later user must discover which crash they are going to get.
- **The vanishing script.** A script solves the problem and stays, unnamed, in the run directory. A month later the same problem is solved again from scratch, slightly differently, with a fresh set of bugs, and the second author never learns the first version existed.
- **The drifting fork.** A copy taken "just to change one flag" stops inheriting; upstream later fixes a correctness bug; the fork keeps the bug and returns silently different answers, discovered only when the two are compared by accident.
- **The unregistered capability.** Built, tested, even documented in its own directory — but no index row. Searching agents conclude the capability does not exist and rebuild it. The entire loss traces to one missing line.
- **The author-facing page.** The documentation explains how the tool works inside and says nothing about when to reach for it or what the output means. The next agent reads the page and still cannot decide, so they write their own.
- **The unlogged upgrade.** Behavior changed; nothing was recorded. The next user's results shift with no way to tell fix from regression, so the tool — rather than the change — loses their trust.
- **Silent-caller breakage.** A patch changes the output format; an unmigrated caller parses the old format and receives values that still parse. Nothing crashes. The wrong numbers travel.
- **The shadow fork.** A modified copy quietly becomes the version everyone actually runs while the index still points at the original. Every property documented about the tool is now a property of the wrong file.
- **Documentation from memory.** The page gets written a week after the tool, reconstructing intent. The one precondition that mattered — the input convention, the case the tool must never be fed — is exactly what the author no longer remembers.
- **The undead duplicate.** A tool superseded by a better one is never retired. Someone finds it in the index, uses it, and gets the answer the replacement was built to correct.

## Checklist

Before writing code:

- [ ] Index searched by capability; the nearest tool's page read in full.
- [ ] One sentence written stating why no existing tool, or a patch to one, covers the need — or the ladder stopped before "write new."

Before the session ends, for any tool created or changed:

- [ ] Change logged, dated, with what a user of the old version would see differently.
- [ ] Four-question page written or updated — does the stated meaning of the output still match?
- [ ] Index row added or updated.
- [ ] Known-answer test exists and passed; the motivating case added to the tests.
- [ ] Every caller of a changed interface migrated.
- [ ] Overlapping tools merged; superseded names carry pointers.
- [ ] Nothing capability-bearing left behind in the working directory.

---

# 证明协议 (Prove Protocol)

> 职责：用 agent 证明：对抗优先管线、怀疑循环、强制多样性——以及命题本身未知时的理论发现

---
name: prove-protocol
description: Multi-agent protocol for proving or refuting mathematical statements. Use when trying to prove a mathematical statement with agents, when a claimed lemma keeps dying under scrutiny, or when the true statement itself is still unknown (theory-finding regime).
---

# prove-protocol — the full proving playbook

## 0. The discipline, and why it is shaped like this

**Within this protocol, no mathematical claim is graded closed on agreement.
It is graded VERIFIED-CLOSED only when an agent assigned to refute it — armed
with executed exact arithmetic — has failed, and when a second agent who
authored nothing has rebuilt the chain from the spec alone, reproducing every
pre-registered value with fresh code.** This is a working standard for agent
output, not a substitute for a refereed or formally verified proof. Everything
below is machinery for manufacturing those two events on purpose.

The paranoia is calibrated to three observations from practice and from the
literature (Sources, below):

1. **Agreement is free.** Provers built on the same or similarly trained
   models share blind spots and converge on the same form — including the same wrong form.
   Consensus measures correlation of priors, not truth. Independence must be
   forced structurally (separate contexts,
   forbidden cross-reading, named-distinct routes), never requested in a
   prompt.
2. **Self-review approves its own bugs.** The reasoning that produced a
   flawed step is the same reasoning that re-reads it and finds it
   convincing.
3. **Talk is a null instrument.** Natural-language-only critique ("step 7
   seems under-justified") does not move a proof's state — a measured null
   (the intrinsic self-correction null measured by Huang, Chen, Mishra,
   Zheng, Yu, Song and Zhou, arXiv:2310.01798, ICLR 2024). The only signal that cannot be socially
   generated is an executed exact computation at a hostile instance; every
   check in this protocol bottoms out in a script that ran.

Two regimes. Know which one you are in before spending tokens:

- **REGIME 1 — the statement is known**: run the pipeline in §1 (target-pin →
  adversary-first hunt → prover/skeptic core → forced-diversity provers →
  fresh-context cross-verify → interface trace).
- **REGIME 2 — the statement is UNKNOWN or keeps dying**: theory-finding (§4).
  The failure smell: you pin formulation after formulation and a competent
  adversary kills each within hours. A consistent pattern: target reshapings
  come from adversaries, essentially never from provers — provers
  do not find theorems; searchers and adversaries do.

## 1. The pipeline core (REGIME 1)

0. **ADVERSARY FIRST (X0)** — reliably the highest-value step per token
   spent. Before any proving run, spend one run hunting the exact witness that
   makes the claim FALSE (in-regime, exact-arithmetic witness). Ladder
   discipline: shift the target ONLY on a certified fire (exact witness,
   inside the claimed regime); a NO-FIRE changes nothing. A certified kill is
   constructive — with pre-registered alternative forms (see step 1), the kill
   licenses the surviving form instead of ending the run.

   *Micro-example of the X0 posture.* Claim: "over the whole family, the
   quantity is minimized at the symmetric configuration." The adversary does
   not read the heuristic argument; it writes a short exact enumerator over
   the family's smallest members and aims it where symmetry arguments die —
   degenerate members, boundary parameters, the smallest asymmetric
   instance. A minimizer that moves at a degenerate member is a certified
   kill, and the witness names the repair (exclude the degenerate class, or
   weaken to non-strict). One agent-run; it often saves ten.

1. **TARGET-PIN as a shared SPEC**: one spec file every prover reads,
   containing (a) the statement/hole verbatim with source citations; (b) a
   MAY-ASSUME list (granted lemmas WITH their stated hypotheses) and a
   MUST-NOT-ASSUME list (the thing being proven); (c) licensed alternative
   delivery forms WITH acceptance criteria ("closes the consuming target at
   the printed exponents; constants may be flagged, exponents may not move");
   (d) an exact test instance T1 — pre-registered rational/integer values plus
   named FAIL conditions ("a route whose T1 prediction fails is DEAD");
   (e) an erratum channel — specs contain bugs (independent arms have
   repeatedly falsified claims that turned out to be bugs in the spec itself,
   not the mathematics), so the spec must
   be correctable without invalidating prover runs already in flight.
   Pre-register which outcome changes what. The pin agent and the X0
   adversary agent are SEPARATE agents — merging them invites an output-cap
   death; any stage mixing statement-extraction with construction dies.

2. **SKEPTIC LOOP** (the highest-yield loop in practice):
   - ONE workfile is the sole shared state; pre-load the skeptic's danger list
     before proving starts.
   - The PROVER drafts the full chain with every displayed identity tied to an
     executed exact-arithmetic script.
   - A hostile fresh-context SKEPTIC does grounded spot-checks at adversarial
     instances and emits machine-readable bug reports —
     `{failing step index, exact instance, value of each side, residual}` —
     never an essay. Prose-only critique counts for NOTHING.
   - Revise against the report. Accept only after 2–3 CONSECUTIVE clean
     fresh-context passes.
   - One SNEAKY-PLANT audit, on a COPY: plant a known-false step and verify
     the harness CATCHES it. If the plant survives, the harness is
     unfalsifiable and the arm is invalid.
   - Any import outside MAY-ASSUME: flag it verbatim, verify it in the source,
     and PRE-REGISTER the downgrade path ("if ruled inadmissible → OPEN-AT
     step k with the rest intact"). This adversarial self-audit is what
     makes one-pass external verification possible.

3. **FORCED-DIVERSITY RIDER** (mandatory): ≥2 extra provers on named distinct
   routes, parallel fresh contexts, no cross-reading. Lesson from practice:
   independent arms converge unanimously on the same form with ease — and the
   artifact that reshapes a target tends to come only from a forced-divergent
   route, at any budget. The redundancy (including DNFs and failed
   certifiers) buys the one artifact nothing else produces.
   RULE: a closure without a diversity pass is
   graded PROVISIONAL. Cheap version: ONE skeptic chain (the proof) + ONE
   small tournament of 2–3 forced-distinct provers (the falsifier).

4. **FRESH-CONTEXT CROSS-VERIFY + INTERFACE TRACE** (both mandatory before
   VERIFIED-CLOSED). Every arm self-grades CLOSED-UNVERIFIED; nothing counts
   until BOTH:
   (a) **verify pass**: an agent that authored NOTHING re-derives the chain in
       its own words under hostile instructions, treats every "clearly" as a
       check-site, writes a FRESH independent enumerator (no code reuse) that
       reproduces every pre-registered exact value, and greps the load-bearing
       imports for circularity. Verdict: CONFIRMED / refuted, constants
       printed.
   (b) **interface ruling**: trace EVERY use-site of the delivered object in
       the consuming document; rule per-site whether the delivered form
       satisfies the consumer's STATED hypothesis (not its wording — wording
       is often shaped like the strong form over content the weak form
       covers); machine-check the composed arithmetic. This is where an
       alternative-form delivery gets legitimized or killed.

## 2. Failure-mode catalogue

Each class is the reason a rule above exists; the vignettes describe
mechanisms, not one-off accidents.

- **Proof by agreement.** Provers converge on the same conclusion and the
  convergence is filed as verification. Mechanism: shared priors produce
  identical errors at any N — the agreement was determined before the first
  token was generated. Cure:
  §1.3 forced diversity plus §1.4(a); a verdict only counts from an agent
  that could have profited by disagreeing.
- **Steps verified by their author.** The prover "double-checks" its own
  chain and reports all steps sound. Mechanism: the blind spot that wrote the
  bug re-approves it. Cure: skeptic and verifier are fresh contexts that
  authored nothing, always.
- **The skipped hunt.** No counterexample search was run because the claim
  "obviously" holds — the heuristic is clean and the small cases in the
  prover's head work. Mechanism: obviousness is a fact about the prover's
  prior, not about the statement; the witness usually
  lives exactly where the intuition was trained not to look (degenerate and
  boundary instances). Cure: X0 is unconditional; it runs first even when
  everyone is sure.
- **Talk-only skepticism.** The skeptic writes paragraphs of doubt, the
  prover writes paragraphs of reassurance, the workfile grows, the proof
  state does not move. Mechanism: language models happily co-author
  confidence. Cure: bug reports are machine-readable; anything without an
  executed instance is noise.
- **The harness that cannot fail.** The verification loop passes everything —
  because it would pass anything. Mechanism: a checker that has never caught
  a planted bug has an unmeasured false-negative rate; its passes carry no
  information. Cure: the sneaky-plant audit — no trust before a demonstrated
  catch.
- **The silent import.** Somewhere in step 9 the chain uses a fact outside
  MAY-ASSUME — often a disguised paraphrase of the target itself. Mechanism:
  circularity arrives dressed as a "standard fact." Cure: the verbatim
  import flag (§1.2) plus the verify pass's circularity grep.
- **The unexecuted certificate.** The journal says "the attached script
  verifies this" and the script was never run to completion; one measured
  "certificate" failed its own pre-registered asserts when actually executed.
  Mechanism: writing a plausible checker and running one are different acts.
  Cure: script-of-record with output quoted verbatim (§3).
- **Verification against wording.** An alternative-form delivery is accepted
  (or rejected) because it matches the consumer's sentence rather than its
  hypothesis. Mechanism: statements are routinely written stronger than
  their proofs use. Cure: the interface trace (§1.4b).
- **The spec trusted as ground truth.** All arms faithfully attack a
  statement mis-transcribed at pin time — an index off by one, a hypothesis
  dropped. Mechanism: the pin has the same error rate as any other artifact.
  Cure: the erratum channel; treat a unanimous early kill as a possible spec
  bug first.
- **Pin-thrash (the zombie statement).** The tenth reformulation of a
  repeatedly-killed claim is being pinned with fresh hope. Mechanism: the
  true object is usually a continuum or a mechanism, not the crisp dichotomy
  being re-pinned; each new pin samples the same doomed neighborhood. Cure:
  switch to REGIME 2 (§4).

## 3. Infrastructure rules (each learned from an agent failure)

- **Skeleton-first, corrected form** (a recurring agent failure shape:
  bulk-read everything, then die at the output cap having planned but never
  written): (1) read the TARGET PIN ONLY; (2) IMMEDIATELY write the
  workfile skeleton, one pre-filled line per planned section; (3) read
  supporting files ONE AT A TIME, per section, transcribing each check into
  its section before opening the next file. Never hold more than one
  unwritten conclusion. For symbolic work: scripts write their own output
  files; quote ≤5-line summaries; never paste large expressions into
  messages.
- **Never steer a running proof agent mid-run** — corrections go in relaunch
  prompts. Mid-run messages trigger a fatal re-planning burst.
- **Disk-incremental journals with executed evidence**: the workfile is the
  proof state; write as you go. Transient infrastructure errors are not state
  changes — resume, never re-derive. A run that dies with zero bytes on disk
  is ungradeable: no journal = no arm. Script-of-record + output file quoted
  VERBATIM in the journal, so graders can replay exactly.
- **AMBIGUOUS-refusal beats silent improvisation**: on a broken or ambiguous
  spec, halt-and-flag or redesign-with-logged-deviation (legal, gradeable).
  Silently improvising out-of-model parameters is a measured downgrade-to-
  OPEN.
- **Detach all compute expected to outlive the agent's turn** (e.g.
  setsid/nohup or your framework's background-job facility); non-detached
  children die with the tool session.
- **Budget honesty**: parallelism premium charged; DNFs and failed certifiers
  count against the arm; the metric is reusable-progress-per-token, not
  closure count.

## 4. THEORY-FINDING (REGIME 2 — when the statement itself is unknown)

The signature of this regime: formulation after formulation gets hand-pinned,
and a competent adversary kills each one within hours or days. When repeated
pins die, STOP hand-guessing and search statement-space mechanically:

**4a. Build the exact evaluator first** (the FunSearch / AlphaEvolve
precondition: generate-and-score against an exact evaluator is the pattern
behind the published machine-discovered mathematics we know of — Romera-Paredes
et al., Nature 625 (2024) 468, doi:10.1038/s41586-023-06924-6; Novikov et al.,
arXiv:2506.13131; Georgiev, Gómez-Serrano, Tao and Wagner, arXiv:2511.02864). Assemble a LABELED CORPUS of every
certified object the effort has produced (witnesses, counterexamples,
controls; label quality = certified/measured/screened as an explicit field,
receipt-traced). Then a FEATURE LIBRARY of computable functionals spanning
the project's mechanistic vocabulary. The corpus + evaluator turn "is this
candidate statement true so far?" into an exact, instant check.

**4b. Forced-distinct THEORY TOURNAMENT**: 2–4 agents, no cross-reading, each
LOCKED to a different organizing principle (e.g., bifurcation /
symmetry-breaking; information geometry; real algebraic geometry;
probabilistic / genericity). Each must deliver: the organizing picture in its
lens; CANDIDATE THEOREMS fully quantified and falsifiable; an explicit
object-by-object consistency table against the certified corpus; the 3
sharpest first tests; honest scoping of which certified objects fall outside
its lens. Divergence between arms is data.

**4c. Invariant synthesis** over the feature matrix (searchers: sparse
inequality synthesis, monotone-lattice search, program search) — candidates
scored by the exact evaluator, survivors handed IMMEDIATELY to an X0
adversary — never pin a synthesized statement that has not survived a
dedicated falsification run.

**4d. Formulation-ladder bookkeeping**: every dead formulation gets its
killer recorded (witness + mechanism). The kill LIST is itself a deliverable
— after enough kills it becomes a theorem-grade impossibility map, and the
mechanisms usually name the surviving statement's true shape (in practice the
kills typically trace to a small number of identifiable degeneracy
structures).

## 5. Preconditions & priors (do not deploy blind)

Published base rates without preconditions, as of the cited evaluations (Mar 2025 /
Feb 2026; capabilities move quickly): 10-15% cold success (pass@1) on fresh self-contained
research lemmas (LemmaBench — Peyronnet, Gloeckle and Hayat, arXiv:2602.24173); <5% average proof score on USAMO 2025
for most models evaluated at release despite strong final-answer benchmark results (Proof or Bluff —
Petrov, Dekoninck, Baltadzhiev, Drencheva, Minchev, Balunović, Jovanović and Vechev,
arXiv:2503.21934). Projects
beat the base rate only when THREE preconditions held — check all three
first:
1. **Exact-computable test instance**: T1 with exact rationals, fully
   enumerable in seconds — every chain and every bug falsifiable by a CAS the
   same hour. Absent this, the skeptic loop degenerates to natural-language
   self-critique (measured null).
2. **A falsifiable, pre-registered alternative**: both forms NAMED in the
   spec with acceptance criteria, so the adversary has a concrete statement
   to kill and a kill constructively licenses the survivor. Absent this, the
   adversary step has no target.
3. **Mature interface**: the consumers of the result already exist with
   stated hypotheses and a may-assume list — quantifier-completion against
   known consumers, not open-sea invention. Absent this, expect the ~15%
   prior.
For REGIME 2 add: (4) a corpus of certified objects rich enough to score
candidates — if you lack one, run adversary/instance-building rounds first.

## 6. What has worked in practice, and what has not

WORKS (in our campaigns and in the literature cited in §5): generate-against-exact-evaluator; self-contained
stuck-step consultation with CAS re-derivation; candidate-object search for
analysis proofs (Lyapunov/ansatz enumeration, falsify-each-cheaply);
decomposition into sublemma STATEMENTS first, split-on-verification-failure;
literature retrieval (typed as retrieval, never as discovery).
HAS NOT WORKED, for us or at the base rates cited in §5: autonomous end-to-end proving without a mechanical certifier;
self-reported confidence; final-answer benchmarks as proving ability;
natural-language-only critique.

Grading: VERIFIED-CLOSED only after §1.4's two passes. Log every run — arm,
budget, grade, artifacts — to a scoreboard so DNFs and failed certifiers
stay visible.

**Sources and acknowledgments.** This protocol was distilled from our own
multi-agent proving campaigns, but its parts have antecedents we are glad to
name: the verification-and-refinement loop of Huang and Yang (arXiv:2507.15855)
and the practitioner techniques collected by Woodruff, Cohen-Addad et al.
(arXiv:2602.03837) — problem decomposition, iterative refinement against error
feedback, and the model deployed as an adversarial reviewer of existing proofs;
counterexample-guided inductive synthesis (Solar-Lezama, Tancau, Bodik, Seshia
and Saraswat, ASPLOS 2006) for the adversary/prover alternation; mutation
testing (DeMillo, Lipton and Sayward, IEEE Computer 11(4) (1978) 34) for the
planted-bug audit; Knight and Leveson's (IEEE Trans. Softw. Eng. SE-12 (1986)
96) demonstration that independently written versions fail together, which is
why diversity is forced rather than requested; and, older than all of these,
Lakatos's *Proofs and Refutations* (Cambridge, 1976). The exact-evaluator
regime follows FunSearch and AlphaEvolve (refs in §4a); the base rates are from
LemmaBench and Proof or Bluff (§5) and the self-correction null from Huang et
al. (§0).

## 7. Closing checklist

- [ ] Regime identified; after two dead pins, the REGIME 2 question was
      asked on the record.
- [ ] Spec file exists: statement verbatim, MAY/MUST-NOT-ASSUME, alternative
      forms with acceptance criteria, exact T1 with FAIL conditions, erratum
      channel.
- [ ] X0 adversary ran BEFORE any prover; fire/no-fire verdict recorded with
      witness or search transcript.
- [ ] Every displayed identity tied to an executed script, output quoted
      verbatim in the journal.
- [ ] Sneaky-plant audit run on a copy; the plant was CAUGHT.
- [ ] ≥2 forced-distinct provers, no cross-reading — else graded
      PROVISIONAL.
- [ ] Verify pass by an agent that authored nothing, fresh enumerator (zero
      code reuse), every pre-registered value reproduced.
- [ ] Interface trace covers EVERY use-site; rulings on stated hypotheses;
      composed arithmetic machine-checked.
- [ ] Imports outside MAY-ASSUME flagged verbatim with pre-registered
      downgrade paths.
- [ ] Journal on disk for every arm; DNFs and failed certifiers logged, not
      erased.
- [ ] Nothing labeled VERIFIED-CLOSED without both §1.4 passes. A wrong
      proof is worse than an honest OPEN.

---

# 模拟审稿 (Referee Sim)

> 职责：外发文档的预审：从它声称的每个受众角度给出最强标准反对意见

---
name: referee-sim
description: Use before circulating any outward-facing scientific document — simulate the strongest standard objection from every audience it claims and verify the document answers each where that reader would look.
---

# referee-sim — the frame linter

Fact-checking and frame-checking are different audits. A verification pass confirms every sentence is true; this pass checks what a reader *concludes*. A document whose every claim is sourced can still mislead by assembly: the caveats live in the body while impressions form in the abstract; the comparison is honest but the baseline is one nobody uses; the theorem is real but the reader leaves believing it covers the case it excludes. That exact failure can survive multiple honesty passes and surface only when an outside expert finally reads the document — the expensive way to catch it, because by then the impression has already formed in the one reader whose report matters.

This is an audit of the IMPLICATURE — what each kind of reader walks away believing — run before anyone outside sees the document. Run your sentence-level style and honesty linter separately; the two passes catch disjoint failures, and neither substitutes for the other.

## Procedure

### 1. Enumerate the audiences, explicitly and in writing

List every community that could plausibly write a report on this document. Sources for the list, in order:

- The introduction's "this matters to X, Y, and Z" sentence. That sentence is a contract; every community it names gets an audit row.
- Every community whose **methods** the document borrows. Using their machinery invokes their standards, whether or not the document ever addresses them.
- Every community whose **results** the document takes as input or uses as a comparison.
- The **incumbent**: whoever currently does the thing the document claims to do better, faster, or differently. This audience exists even when the introduction never mentions them — especially then.
- The **practitioner** who would act on the result, whose question is never "is it interesting" but "what breaks if I rely on this."
- The venue's general reader, who determines which claims must survive without the surrounding expertise.

Two rules. First, any community borrowed from for authority — a method, a dataset, a benchmark, a motivating application — gets a row without exception; the missing-audience failure below is almost always one of these. Second, a claim of interdisciplinarity RAISES the bar. Each additional audience brings its own standard objection, and outsiders read less charitably than insiders: they apply their home field's first-order standard and have no reason to extend the benefit of the doubt.

### 2. Generate each audience's strongest STANDARD objection — on two axes

For each audience row, generate two separate objections:

- **Correctness**: "is this right, and does it hold in the cases my community cares about?"
- **Novelty**: "is this new, and what exactly is the advance over what we already do?"

These are different referee reports, answered in different places — correctness in scope statements, controls, and comparisons; novelty in the introduction's positioning and its engagement with prior work. A document that answers only one axis dies on the other, and conflating them produces a characteristic hybrid: a document that proves everything and never says what is new, or one that claims a first while the incumbent community's state of the art goes unexamined.

"Standard" means the first thing that community's referee asks, not an exotic one. Calibration by community type:

- *Engineering/applications*: "does this survive the generic case (generic noise, generic inputs, adversarial settings), or only the structured case you studied?"
- *Experimentalists*: "what does the apparatus actually measure, and is it the same object you computed? Which parts of the prediction survive the differences?"
- *Numericists*: "is anything converged? In which units or scheme — and does the flattering choice hide the drift? What is the null hypothesis your signal must reject?"
- *Formal theorists*: "is the named object well-defined here (does the symmetry, charge, or protection actually exist in this setting)? What is conjecture vs theorem, and does the abstract distinguish them?"
- *The incumbent method's community*: "we already do this better — what is your edge, precisely, and have you checked our state of the art?"

### 3. Steelman every objection

The objection must be one a well-informed, unsympathetic expert would sign — steelmanned, never strawmanned. Three tests:

- **The sting test.** If the document as written already answers the objection cleanly, you have probably written a weak one; sharpen until acting on it would require an edit. Occasionally the document really has pre-answered the strongest standard objection — treat that verdict as suspect and earn it, because a clean sweep is also exactly what a strawman pass produces.
- **The knowledge test.** Write the objection in the referee's own voice and name what they know that the document ignores: the prior result, the standard control, the benchmark their community demands. If you cannot name what the objector knows, you have not simulated them; you have simulated yourself in their seat.
- **The lead test.** A real referee leads with the standard objection. If your simulated objection is clever but nonstandard, generate the standard one first; the exotic one may follow as a second row, never as a substitute.

### 4. Verify each answer sits where the objector would look

Hostile readers read in a fixed order: title, abstract, figures, conclusions — then, only if still engaged, the one section their objection lives in. "Derivable by assembling facts scattered across the document" is a FAIL: the test is whether the objector meets the answer on their actual reading path, at or before the point where the objection forms. A disqualifying caveat that first appears mid-body has already lost — the report was drafted at the abstract.

Severity: **HIGH** — unanswered objection a referee would lead with, or a claim the project's own data or files contradict. **MEDIUM** — answered in the body but absent where the impression forms. **LOW** — answered, could be more prominent.

### 5. Audit the abstract separately and last

The recurring failure: body honest, abstract clean of every caveat. The abstract must carry (a) any scope limitation a claimed audience would consider disqualifying if discovered later, and (b) conjecture-vs-established labeling for the headline claim. Audit it cold, as someone who will read nothing else — most referees form their frame there, and some readers are abstract-only.

### 6. Apply minimal defensive edits only

Scope sentences, null-hypothesis statements, prominence moves (caveat from body to abstract or scope paragraph), unit and convention consistency for headline numbers, conjecture labeling, terminology corrections. NO new claims, NO new results, and no hedge-blur: the correct response to an objection is one sentence stating the claim's boundary, never a softening of the claim everywhere it appears. Run all new text through the machine-voice/honesty linter; recompile or re-render and confirm clean.

### 7. Write the verdict table

To `referee_sim_<doc>.md` beside the document: audience / objection / axis (correctness or novelty) / answered-where-or-NOT / severity / fix applied. The table is the deliverable even when no edits are needed — it records that the audit ran and what it covered, and the next revision's audit starts from it.

## Failure-mode catalogue

- **The friendly reader.** The simulated referee inherits the author's framing and raises only objections the document already answers; the pass returns clean, and the first genuine outsider leads with something the audit never generated. This is how the audit itself fails, and the reason for the sting test and the fresh-context rule.
- **The strawman objection.** A cousin of the friendly reader: each objection is phrased just weakly enough that the existing text answers it, so the verdict table fills with reassuring rows and the audit certifies the very frame it was built to attack.
- **The unread answer.** The objection is answered — thoroughly, honestly — in a subsection the objector never reaches. The referee formed the objection at the abstract and drafted the report before meeting the answer. Prominence is part of the answer, and an answer off the reading path is no answer.
- **Novelty–correctness conflation.** One objection per audience instead of two. The document defends correctness exhaustively and never states its advance over the incumbent, or claims an advance while a prior result the incumbent community knows goes unengaged. Either way the report writes itself.
- **The missing audience.** A community whose method, dataset, or benchmark the document borrows never gets a row — and it is exactly their standard objection that goes unanswered, because the borrowing invoked their standards without the audit noticing.
- **The abstract firewall.** Every caveat lives in the body; the abstract is clean. Sentence-level honesty passes confirm each sentence individually and never see the assembly. Impressions form in the abstract; the body is the appeal, and most readers never hear the appeal.
- **The charitable outsider.** The audit assumes a second field will read generously because the work is outside their specialty. The opposite holds: outsiders fall back on their home field's first-order concern and bring none of the insider's context for why a shortcut was reasonable.
- **Hedge-blur.** The fix pass answers an objection by weakening the claim everywhere instead of scoping it once. The document now claims less than it established, reads as unconfident, and still leaves the objection unanswered.
- **Author-context contamination.** The audit runs in the same context that wrote the document, so the "referees" judge each objection answered the way the author already did, blind spots intact. Distinct from the friendly reader: here even a well-generated objection receives a self-serving verdict on whether and where it was answered.

## A worked example

A document claims a faster method for a standard computation, demonstrated on a class of structured instances. The audience table, before any objection is written:

| audience | why they get a row |
|---|---|
| incumbent method's community | the document claims to beat them |
| practitioners of the computation | they would act on the claim |
| numericists | the evidence is numerical |
| the structured-instance community | their instances serve as the benchmark |

Steelmanned objections: the incumbent, on the novelty axis — "your comparison baseline is an implementation nobody uses; our current version handles your benchmark class in comparable time." The answer must live in the comparison section AND the abstract's claim must scope to what was actually beaten. Practitioners, on the correctness axis — "does this survive generic instances, or only the structured class you demonstrated?" The answer belongs in the scope paragraph and the abstract, since a practitioner discovering the restriction later would consider it disqualifying. Numericists — "converged in what sense, and against what null?" The answer belongs beside the headline figure, where the convergence impression forms. None of these objections is exotic; each is the first question its community asks. A version of this document that answers all three in those places is a materially safer document than the one that merely contains the answers somewhere.

## Cross-checks that pay off (run them every time)

- **Headline-number units**: is the quoted number in the same units and convention the document's own equations define? (Failure shape: a drift quoted in a convenient intermediate scheme's units comes out at roughly half the value the paper's own equations define — the flattering choice hides a factor of two.)
- **Claims vs the project's own files**: search the result notes for statements the document contradicts. (Failure shape: a document asserts a quantity must shrink with system size while the project's own larger-size results show it growing.)
- **Necessity language**: every "must / guarantees / ensures" — is it derived, or is it hope written as necessity?
- **Null hypothesis**: for any claimed signal (degeneracy, convergence to a special value, pattern), does the document state what chance would look like and why the data rejects it?
- **Temporal honesty**: if an interpretation was found *after* the data forced it, the document may present theory-then-confirmation; restore the actual order. Independent prior results can still be cited as independent.
- **Conjecture labeling at the title and abstract level**: "candidate / consistent with / designed for" vs language implying the claim is established.

## Operational notes

- Run the pass in a **fresh agent context** — never the context that authored the document. The simulated referees must not inherit the author's framing (see the catalogue's last entry).
- The cost is one agent session per document. Against a referee report that leads with the objection you failed to simulate, it is cheap.
- The exercise is a pre-mortem in Gary Klein's sense (Harvard Business Review, September 2007) run per audience.

## Expected yield (why this pass is mandatory)

First runs of this pass on finished, fact-verified documents reliably surface findings, often HIGH-severity ones: a generic-case scope statement missing from exactly the place an outside expert looks first; an abstract with no conjecture language over a fully-caveated body; a units choice that flatters a headline convergence figure; a claim the project's own files contradict. Each of these is a future referee-report finding, which is why the pass runs before circulation rather than after.

## Checklist

- [ ] Audiences enumerated in writing, including every borrowed-authority community and the incumbent.
- [ ] Two objections per audience — correctness and novelty — generated separately.
- [ ] Every objection passes the sting, knowledge, and lead tests.
- [ ] Every answer located on the objector's reading path, at or before where the objection forms.
- [ ] Abstract audited cold, last, as an abstract-only reader.
- [ ] Fixes are scope statements and prominence moves, never hedge-blur; new text linted.
- [ ] Verdict table written beside the document, even when no edits were needed.
- [ ] The pass ran in a fresh context.

---

# 文献综述 (Lit Review)

> 职责：新颖性声明背后的文献审计：全文阅读、可证伪的彻底性、双向引用链

---
name: lit-review
description: Deep literature review behind a research project's novelty claims — a protocol whose one job is to prevent shortcuts. It demands the papers be actually read (nothing from memory), makes thoroughness falsifiable (read ledgers, search receipts, gap statements), tracks citation chains in both directions, and lists the places to look. Use before any novelty claim ships, when writing or reviewing a related-work section, and when refereeing.
---

# lit-review — no shortcuts

A literature review fails silently. Every other check in this harness fails
loudly — a control that doesn't recover the planted answer, digits that
disagree with the independent route. A missed paper produces no error message:
the review reads as complete, the claim goes out, and the miss surfaces later,
from a referee or from the missed author.

Examined afterward, every miss traces to a shortcut that felt reasonable at
the time: the searchers verified the papers they already knew instead of
hunting the ones they didn't; queries stopped a year or two short of the
present; abstracts were read where full texts were owed; a paywall quietly
downgraded a paper from "read" to "skimmed". None of these announce
themselves. The protocol's answer is to make each one visible: every form of
thoroughness claimed here is backed by a receipt a second reader can check, or
it does not count.

Refereeing runs the same protocol in reverse — the submission's novelty
claims become C1..Cn and the verdicts belong to someone else's paper. When
refereeing, follow the venue's rules on AI assistance and manuscript
confidentiality; many prohibit sharing a manuscript under review with AI tools.
Where that is the rule, run this protocol on the public literature around the
submission's claims, never on the confidential text itself, and disclose the
assistance to the editor if the venue asks.

## The proximity scale

Grade every candidate work as you go; the heavy obligations below key off the
grade.

- **P0–P1** — same broad area, different question. Note or discard.
- **P2** — shares a component (a technique, a dataset, a subresult) but not
  the question. Goes in the credit list.
- **P3** — attacks the same question with different tools, or a neighboring
  question with the same tools. Full-text read required.
- **P4** — overlaps part of a claim: a special case proved, or the same
  result under different assumptions. Full-text read, verbatim quote, chains
  both directions.
- **P5** — contains the claim. The review's reason for existing.

## The three iron rules (violations invalidate the review)

**1. Read the papers. Nothing from memory.**

- Every work graded P3 or above is read in full text — the PDF fetched and
  read, not the abstract, not another paper's summary of it, not what the
  model remembers. The relevant theorem, definition, or construction is
  quoted verbatim with a page or section number. If the full text cannot be
  obtained (paywall without institutional access, no author-posted copy),
  the work is marked FULL-TEXT-UNREAD and its grade is a ceiling estimate, flagged as such —
  never silently downgraded to what the abstract suggests.
- No citation, date, venue, or claim about what a paper shows comes from
  memory. Memory generates the search query; the source generates the
  sentence. Verification means a live fetch of the primary record (publisher
  page, preprint server, author PDF), with the route recorded.
- Gated or scanned PDFs: use legitimate routes only — an open-access or
  preprint version, the author's own posted copy, your institution's
  subscription, interlibrary loan, or a request to the author; read a scanned
  PDF page by page with vision if that is what it takes. Never bypass access
  controls or use unauthorized repositories. If no legitimate full text is
  available, mark the work FULL-TEXT-UNREAD (grade = ceiling) and list it as
  owed.

**2. Thoroughness is falsifiable, not asserted.** Every review carries
receipts:

- **A search ledger** — every query actually run, on which engine or index,
  with the year range. A query that never named the current year is a defect.
- **A read ledger** — which works were read full-text, which abstract-only,
  which flagged unread. A review whose read ledger is empty at P3+ is not a
  review.
- **A gap statement** — what was NOT searched: fields, languages, venues,
  year ranges, any channel that died on a budget or access wall. Implied
  completeness is the exact lie this skill exists to prevent.
- **Iterate to dry** — rounds continue until a fresh round (a new angle, a
  recency re-sweep, chains run on newly found works) returns nothing at P3+.
  Report the rounds run and what each added. One pass has never been enough.

**3. Track citation chains, both directions.** For every work at P3+:

- **Backward** — mine its reference list for ancestors no search named.
  Record the chain (A cites B cites C): the chain is itself a deliverable,
  because it is how the next reviewer verifies coverage.
- **Forward** — find who cites it: cited-by listings sorted newest first, the
  most recent two or three years read closely. This is how you find the paper
  whose name you don't know — it cites the ancestor you do.
- **Per-author recency** — every author appearing at P3+ gets their last few
  years swept through the current month: personal website (publications and
  preprint pages, including linked working papers — drafts are often posted
  there long before journals), profile pages sorted by date, preprint and
  working-paper listings. Publicly posted drafts and working papers count
  fully.

## Places to look

Use every service within its terms. Prefer documented APIs (Semantic Scholar,
OpenAlex, Crossref, arXiv, INSPIRE, PubMed, ADS); query interactive-only
services such as Google Scholar by hand or at human pace, never from a fan-out
of agents; rate-limit every automated fetch (pause ~2 s between calls) and
honor robots.txt; list any service you could not lawfully query in the gap
statement.

Tick each, or put it in the gap statement:

- **Google Scholar** — keyword and quoted-phrase queries; cited-by chains;
  author profiles sorted by year.
- **Semantic Scholar** (site and API) — citations and references
  programmatically; good recall on preprints.
- **The field's preprint server** — arXiv by category plus full-text search,
  bioRxiv/medRxiv, SSRN, OpenReview for machine-learning-adjacent claims. The
  frontier lives here and on authors' pages, not in journals.
- **Working-paper series**, where the field has them — institutional series,
  author listings, new-paper feeds.
- **Author websites** — read the publications page, CV and any preprints or
  drafts the author has publicly linked; the newest work is often posted there
  before any index has crawled it. Do not guess URLs or enumerate directories.
- **Review articles, surveys, handbook chapters** in the claim's territory —
  a field's own synthesis is a pre-built citation chain; read the newest one
  you can find.
- **Journal tables of contents**, the last couple of years, for the three or
  four venues where the nearest ancestors published.
- **Course syllabi and lecture notes** (site:edu filetype:pdf) — instructors
  track frontier papers faster than journals, and usually link the preprint
  version.
- **Software registries** (CRAN, PyPI, the package archives of statistical
  environments) — a rival method often exists as a package before or beside
  its paper.
- **Dissertations** — when a research line's students are active, the newest
  statement of the line is a thesis.
- **Field review databases** where they exist (zbMATH, MathSciNet,
  INSPIRE, PubMed).
- **The claim's own vocabulary, and every synonym.** Search the project's
  coined terms in quotes, plain paraphrases, and the whole synonym family —
  the same object wears a different name in every field that touched it.
  Build the synonym list as you go and re-run every search under each new
  name found. The phrase hunt does two jobs: it protects your naming, and it
  finds the rival wearing another field's name for your object.

## Procedure

**0. Claims first.** Before any search, write the numbered novelty claims
C1..Cn, plus the exact headline sentences the paper or announcement will
carry. Each headline gets a verdict at the end: survives as worded /
falsified (quote the falsifier) / survives only reworded (propose the
wording). A review run without pinned claims drifts into confirming a mood.

**1. Fan out by lineage.** One searcher per lineage or subfield that could
own the result — six to twelve angles for a serious claim (parallel
subagents if your framework supports them; sequential passes otherwise). Any
known-relevant names in a brief are a floor, never the hunt list: a searcher
told "check Smith and Jones" will verify Smith and Jones and under-search
everyone else. Each angle keeps its own ledgers.

**2. Chains and recency** (iron rule 3) on everything the angles surface at
P3+. This is where the papers no query can name get found.

**3. Synthesize.** A deduplicated table of the closest works — P4/P5 entries
with verbatim quotes and locations — plus a credit list (P2–P3), diffed
against the paper's actual bibliography. Then per-claim novelty verdicts,
stated against interest: (a) new as far as this review can see; (b) new with
required credit — name the ancestor; (c) at risk as worded — name the work,
quote the overlapping passage, propose the wording that survives. No
softening. The verdicts are the product; a review that returns only a reading
list has not finished.

**4. Iterate to dry** (iron rule 2), then carry the findings into the paper.

## Findings into the paper

- **Prior work is motivation, never a rival.** The closest ancestor goes in
  the introduction as the point of departure, credited generously BEFORE the
  delta is stated; the delta is then stated flat. Cut protective register on
  sight ("a referee will note", "to be clear about priority") — prose that
  argues with an imagined referee reads as exactly what it is.
- Every citation added to the paper is copied from the review's verified
  entries only, with the verification route noted (the ref-check skill
  governs entry format and bibliography audits).
- At-risk claims are reworded before anything goes out. A headline that
  failed its verdict never survives on "approximately true".
- P2–P3 works land in the credit list even if never cited — the next
  revision reads the list, not the reviewer's memory.
- Full-text debts that remain (a gated text, a book checked only at page
  level) are listed, not forgotten.

## Failure-mode catalogue

Each of these is a class observed in real reviews. When a review misses
something, find the miss's class here — or add it; a miss without a new
entry is a repeat waiting.

- **Canon anchoring.** The brief names the famous papers; the searchers
  verify the famous papers; the miss is the recent work by an author nobody
  named. Verification effort concentrates on what you already know — hunting
  effort must be budgeted separately.
- **Recency blindness.** Every query implicitly ended a year or two ago
  because the searcher's sense of the field did. A central author's latest
  papers sat unfound because nothing swept their output through the current
  month.
- **Venue bias.** Searches favored journals; the field's actual frontier was
  on preprint servers and authors' own sites, months to years ahead. The
  decisive miss was a working paper posted on an author's own website that no
  index had crawled.
- **The abstract-grade read.** An abstract-level skim reported a prior paper
  as claiming the opposite of the project's result; the full text showed the
  same sign and a different magnitude. A false confrontation was minted and
  repeated before anyone read the paper. Full-text reads are not overhead —
  they are where the review's claims come from.
- **Memory-sourced citations.** An entry written from recall carries a
  paraphrase of the title, a plausible-but-wrong year, a truncated author
  list — and every field of it reads fine. The cure is upstream of any
  bibliography audit: nothing enters the review from memory.
- **Synonym blindness.** The rival existed for years under another field's
  name for the same object. Every query used your field's term; every one
  returned nothing; "nothing found" was true and worthless.
- **The silent dead channel.** A search or fetch budget ran out mid-review
  and a whole channel — the one that finds author drafts, say — went dark
  without any step failing. The angles reported normally; coverage had
  silently shrunk. Any searcher that hits a budget or access wall says so in
  its gap statement (which channel, which queries never ran), and the
  synthesis counts a dead channel as an owed round, never as covered. A
  review is not dry while a named channel died on budget.
- **One-pass certainty.** The first pass found nothing close, and the review
  stopped there. Distance from the literature on pass one usually measures
  the queries, not the literature.
- **Confirmation search.** Queries phrased to confirm novelty ("first proof
  of X") rather than to destroy it ("proof of X", each synonym, each
  ancestor's forward citations). The reviewer's job is to kill the claim; a
  review that wants the claim to survive will let it.
- **The convenience downgrade.** A paywalled P4 candidate quietly became
  "checked" on the strength of its abstract because the PDF was hard to get.
  The grade kept its authority; the reading behind it was gone.
- **Implied completeness.** The review reported everything it found and
  nothing it skipped. The reader took the union to be the whole field; the
  gap statement existed to prevent exactly that inference, and wasn't
  written.

## Two micro-examples

**The synonym family.** A project coins "anchored window" for its object.
The same object, in neighboring literatures, goes by tolerance region,
feasibility band, and admissible set — each in a literature that never
cites the others. A review that searches only the coined term and its
plain paraphrase returns clean and is wrong. The working method: every time a
P3+ paper names the object differently, that name becomes a fresh round of
queries across every engine already used. The synonym list at the end of the
review is a deliverable.

**The chain that finds the unnameable paper.** You cannot query for a paper
you have no words for. But if it exists, it almost certainly cites the
ancestor you DO know. Take the strongest known ancestor, open its forward
citations sorted newest first, and read the last two years of titles
closely. This is the highest-yield single move in the protocol, and it is
exactly the move a keyword-only review never makes.

**Sources and acknowledgments.** The search ledger, read ledger and gap
statement are a lightweight form of the PRISMA 2020 reporting items (Page et
al., BMJ 372 (2021) n71); citation chaining in both directions is the
snowballing procedure of Wohlin (EASE 2014), whose value over database search
alone Greenhalgh and Peacock measured (BMJ 331 (2005) 1064). We thank the teams
behind Semantic Scholar, OpenAlex, Crossref, arXiv, INSPIRE-HEP, PubMed and
NASA ADS, whose open APIs make the ledgers checkable.

## Exit checklist

- [ ] Claims and headline sentences pinned before the first query.
- [ ] Every P3+ work read full-text with a verbatim quote and location, or
      explicitly flagged FULL-TEXT-UNREAD with its grade marked as a ceiling.
- [ ] Search ledger present; queries name the current year.
- [ ] Read ledger present and non-empty at P3+.
- [ ] Gap statement written — including any channel that died on budget or
      access, counted as owed, not as covered.
- [ ] Chains run both directions on every P3+ work; per-author recency swept
      through the current month, authors' own publication pages included.
- [ ] Synonym family built; every engine re-queried under each name found.
- [ ] The final round added nothing at P3+ (iterated to dry); the number of
      rounds reported.
- [ ] Per-claim verdicts stated against interest; at-risk wording fixed
      before anything goes out.
- [ ] Credit list diffed against the actual bibliography; every added
      citation traces to a verified entry.

---

# 参考文献核查 (Ref Check)

> 职责：对照权威来源核验书目；民间传说式错误陷阱

---
name: ref-check
description: Careful bibliography verification and entry-addition for papers — verify every author, title, journal, volume, pages, year, arXiv ID, and DOI against authoritative online sources (INSPIRE, arXiv, CrossRef/DOI, zbMATH, publisher) before anything enters or stays in a .bib file. Use whenever adding bib entries, auditing a bibliography, checking citations, fixing references, or when asked to "check the references". Encodes the report-then-fix pattern for full-file audits and the folklore-error traps (wrong years, truncated author lists, mislabeled keys).
---

# ref-check — careful reference verification

## The iron rule, and why it exists

**NEVER guess or trust-from-memory an arXiv ID, journal reference, year,
author list, page range, or title.** Every factual field is verified against a
fetched authoritative record before an entry is added, approved, or "fixed."
Training-data recall of bibliographic details is a *hypothesis to verify*,
never a source. If a field cannot be verified after trying at least two
sources, it is FLAGGED, not silently kept or invented.

The rule is this severe because bibliographies are not copied from sources —
they are copied from *other bibliographies*. An error, once printed, outlives
its origin: the next hundred authors copy the entry, not the paper, and the
error acquires the authority of repetition. A language model trained on that
literature has learned the majority text, which for a propagated error IS the
error — model recall of a reference reproduces the folklore version with full
confidence. This is why "it looks right" is worthless here, and why an entry
that half the field cites one way can still be wrong. Verification means
fetching the record closest to the publisher and comparing field by field;
nothing else counts.

A second consequence: an entry that a model *drafted* from memory is not a
degraded citation — it is a fabrication with correct formatting. The observed
pattern (see traps below) is a real identifier carrying invented co-authors,
a paraphrased title, or another paper's journal block. Plausibility is the
failure mode, not the reassurance.

## Authoritative sources, by literature

The universal spine is **CrossRef / the publisher's DOI landing page** —
canonical journal, volume, pages, year for anything with a DOI. Around it,
use the registry native to the literature:

1. **INSPIRE-HEP** (physics/hep) — fetch BibTeX directly:
   `https://inspirehep.net/api/literature?sort=mostrecent&size=1&q=arxiv%3A<ID>&format=bibtex`
   (URL-encode `:` as `%3A`; old-style IDs URL-encode the slash: `q=arxiv%3Ahep-ph%2F<YYMMNNN>`).
   Cross-check the arXiv abs page.
2. **arXiv abs page** (`https://arxiv.org/abs/<ID>`) — title, full author
   list, journal-ref line. v1 titles sometimes differ from the published
   title; **the published title wins** when the entry cites the journal.
3. **CrossRef / publisher DOI page** — the arbiter for journal fields.
4. **zbMATH / MathSciNet / Project Euclid / numdam** — mathematics.
5. **ADS** — astronomy; **PubMed/PMC** — life sciences; **DBLP** — computer
   science (conference/proceedings metadata that CrossRef often garbles).
6. **Zenodo / the software's own CITATION file** — software and datasets.
7. **Gallica / archive.org / WorldCat / publisher record** — classical books
   and pre-DOI literature.

**Search aggregators (Google Scholar, Semantic Scholar) are for FINDING a
work, never for verifying it.** They merge records, inherit upstream errors,
and invent metadata for scraped PDFs. Once found, verify against the native
registry or publisher.

Sleep ~2s between external calls; try a second source before declaring
anything unverifiable. When two authoritative sources disagree, the one
closest to the publisher wins for journal fields, and the disagreement itself
goes in the audit log — it usually marks a folklore error in the losing
source.

## Field-by-field comparison (semantic, not textual)

- **Authors** — every author present, correct order, correct spelling
  *including diacritics*. TeX escapes vs unicode (`{\'e}` = `é`) are equal. A
  missing, extra, or misspelled author = FIX. Watch homonyms: same-surname
  collaborators are routinely merged into one person, and given names swapped
  between them.
- **Title** — word-level. Brace/capitalization/TeX-markup differences =
  formatting. Wrong, missing, or extra words = FIX.
- **Journal, volume, number, pages, year** — exact. Standard abbreviation vs
  full journal name = MINOR. Wrong volume/pages/year = FIX. Translated-journal
  pairs (Russ. Math. Surv./Uspekhi Mat. Nauk; Sov. Phys. JETP/ZhETF): either
  is fine if internally consistent; a mismatched year between the pair = FIX.
- **arXiv ID, DOI** — exact, and the DOI must *resolve to the right work*:
  fetch the landing page and compare its title. A syntactically valid DOI
  pointing at an erratum, a comment, or a different paper by the same group
  is a FIX that no string comparison catches.
- **Entry type and roles** — chapters in collections credit the chapter
  authors, with editors as editors; proceedings carry the conference year vs
  publication year distinction explicitly.

Classify each entry: **OK** (every factual field compared against a fetched
record and matching) · **MINOR** (formatting only, no action) · **FIX** (any
factual discrepancy — record `field: ours -> authoritative` + source URL) ·
**UNVERIFIABLE** (state exactly what was tried) · **INTERNAL**
(self-references/companion notes — list, exempt).

Never mark OK without having actually fetched and compared. "Looks right" is
not a verification.

## Folklore traps (all observed in practice)

Each of these is a measured failure mode from real bibliography audits, not a
hypothetical. They are the classes that survive casual checking because the
entry *looks* healthy.

- **Wrong years that circulate** — a result becomes attached to the wrong
  year and the whole literature repeats it: e.g. a landmark irrationality
  theorem published in 2001 that half the citing literature dates to 2004 —
  the journal record, not the majority citation, is the evidence.
- **Truncated author lists** — the field remembers the famous pair and drops
  the rest (e.g. a four-author paper that the field routinely cites by its
  two most famous authors). Verify the FULL list even when the short form is
  universal.
- **Merged authors** — two distinct people fused into one: same surname,
  averaged initials, one entry where the record shows two names. The inverse
  also occurs — one author split into two by an initials variant.
- **Phantom page numbers** — a plausible page range attached to a paper that
  the journal published under an article number, or a first page copied from
  a different paper in the same issue. Article-number journals take the
  article number, not an invented range.
- **Mislabeled keys** — the entry under a key can be a *different paper* than
  the key name suggests (observed: a key naming one author trio holding a
  paper by a different trio). The key is part of the audit: check that key ≈
  actual authors.
- **Announcement vs final version** — cite the cleanly citable version
  (book/journal), not a short announcement note, and say which in a comment.
- **Preprint v1 title drift** — published title wins.
- **Prose initials vs keys** — before renaming a key, grep every `\cite`
  usage AND read the surrounding prose: initials in prose may already refer
  to the *correct* authors even when the key is wrong.
- **Another paper's journal block** — an entry can carry the correct
  preprint ID/title with the journal/volume/pages/year of a *different* paper
  by the same authors (observed in practice). Verify the journal ref against
  the preprint server's own journal-ref line or CrossRef, not just "a" record
  by those authors.
- **Descriptive phrase as title** — entries written from memory often carry a
  paraphrase of the paper's subject instead of its actual title (observed
  five times in a single audit). Titles must be copied from the fetched
  record, never composed.
- **Invented co-authors / wrong given names on real papers** — LLM-drafted
  entries can attach plausible-but-wrong names to a correct identifier
  (observed: wrong given names on 3 entries, an extra co-author on 1, in one
  audit). Check every name against the record even when the ID resolves.
- **Entirely wrong paper under a plausible key** — key, note, and citing
  prose describe paper X while the entry's fields are paper Y (observed: an
  entry on one subject sitting under a key naming a different subject
  entirely). When key/note/prose disagree with the entry, read the *citing
  prose* to determine intent before fixing — the correct fix may be a new
  entry, not a field repair.
- **A "verified" pass is not immune** — one same-day verified addition
  carried wrong volume/pages from a hasty read of the abstract page (an
  off-by-one volume number). Volume/pages come from the journal-ref line or
  CrossRef, not from adjacent metadata on a page that lists several versions.

## The claim check — does the cited work say what the sentence says?

A bibliography can be field-perfect and still lie, because the citation's
real payload is the *sentence attached to it*. A full ref-check audits both
layers. For every citation that carries factual weight — "X proved Y [12]", a
number with a bracket after it, a definition attributed to a source, a
"first shown in" — do this:

1. **Open the work.** Full text where available; the preprint version
   otherwise (note the version skew). The abstract alone verifies only
   abstract-level claims.
2. **Locate the claim**: the theorem number, equation, table, or page where
   the cited statement actually appears. Record the locator in the audit log
   — a claim check without a locator is an impression, not a check.
3. **Verdict per claim**: **SUPPORTED** (locator recorded) · **DRIFTED** (the
   claim is true but lives in a different work — often an earlier or later
   paper in the same series; fix the citation, not the prose) · **INFLATED**
   (the work proves a special case or a weaker form than the sentence
   asserts) · **ABSENT** (nothing in the work matches) · **CONTRADICTED**
   (the work says the opposite — it happens, usually via a sign, a
   convention, or a negation lost in paraphrase).
4. **Report, never silently rewrite.** For DRIFTED the fix is the citation;
   for INFLATED/ABSENT/CONTRADICTED the fix may be the prose, and that is the
   author's call. A checker who "fixes" meaning has exceeded the mandate.

The claim-layer traps mirror the field-layer ones: **secondhand laundering**
(the citation and its misreading were both copied from an intermediary paper
that itself never checked); **review-article telephone** (a survey's
compressed paraphrase gets cited as if it were the original's claim);
**attribution creep** ("first proved by" pointing at the famous paper when
the record shows an earlier, obscurer proof); **convention mismatch** (the
cited formula is right in the source's normalization and wrong in the citing
paper's). None of these are visible from the bibliography file; they only
fall to actually opening the work.

## Process

### Adding entries (small batches)
Verify each work per the rules above; match the house entry style of the
target .bib; add under a dated comment block
(`%% ----- <purpose> (added <date>, verified)`) with a per-entry
`% VERIFIED <date> <source-URL>` comment; run a duplicate-key check
(`grep '^@' | extract keys | sort | uniq -d` must be empty); never modify
existing entries in the same pass. Also run a duplicate-*work* check: the
same paper can already sit in the file under a different key, and two keys
for one work will bite at citation time.

### Full-file audit (report-then-fix pattern)
1. **Chunk** the .bib by entry boundaries (~15–20 entries per verifier;
   compute line ranges from `grep -n '^@'`).
2. **Verify in parallel, REPORT-ONLY** — if your agent framework supports
   parallel subagents, fan the chunks out; verifiers never edit the .bib
   (concurrent writes corrupt it). Each returns structured per-entry verdicts
   with verbatim diffs and source URLs.
3. **Fix serially** — one pass (human-reviewed, or a single agent working
   from the approved diff list) applies FIX items only, keys unchanged unless
   a rename is explicitly approved.
4. **Key renames are load-bearing** — grep all `\cite` usages across the tex
   tree, update them atomically with the .bib, check prose initials (see
   traps).
5. **Rebuild** — full compile-plus-bibliography cycle (e.g. pdflatex+bibtex);
   zero errors, zero missing/undefined citations is the exit gate. A clean
   exit code is not the gate — read the log for warnings, and confirm the
   rendered bibliography actually carries the fixes (stale .bbl files
   survive successful-looking builds).
6. **Record** — stamp fixed entries `% VERIFIED <date> <source>`; log the
   audit (date, counts by verdict, fixes applied) wherever the project tracks
   provenance. The log is what lets the next audit skip re-fetching two
   hundred already-verified records — an unstamped verification evaporates.

## Exit checklist

- [ ] Every entry has a verdict; zero entries skipped.
- [ ] Every FIX applied cites its source URL; every UNVERIFIABLE is flagged
      to the user, not silently retained.
- [ ] Every DOI resolved and its landing page compared, not just
      string-checked.
- [ ] Claim check done on every load-bearing citation, with locators
      (theorem/equation/page) recorded; DRIFTED/INFLATED/ABSENT/CONTRADICTED
      verdicts reported to the author, prose untouched.
- [ ] Duplicate-key and duplicate-work checks clean; all `\cite` keys in the
      tex tree resolve (bibliography log has no missing-entry warnings).
- [ ] Full rebuild passes with zero errors and zero undefined citations, and
      the rendered output carries the fixes.
- [ ] Audit logged with date, counts by verdict, and fixes applied.

Acknowledgment. This procedure leans entirely on open bibliographic
infrastructure — INSPIRE-HEP, arXiv, Crossref, zbMATH Open, MathSciNet, NASA
ADS, PubMed and DBLP; we are grateful to the people who maintain them. Work that
relied on ADS should carry the acknowledgment its FAQ asks for ("This research
has made use of the Astrophysics Data System, funded by NASA under Cooperative
Agreement 80NSSC21M00561").

---

# 科学文风检查 (Prose Lint)

> 职责：科学散文 linter：炒作词汇、空结构、无 agent 的散文、诚实性与数字核查

---
name: prose-lint
description: use before circulating any scientific text, human- or LLM-drafted — a clarity and integrity linter: hype vocabulary, empty sentence structures, agentless prose, number discipline, and honesty failures; one pass is never enough.
---

# prose-lint

**THE MASTER TEST, before and above every class below: read each sentence and
ask — would a specific human scientist say this, out loud, across a table to a
colleague? Not "is it grammatical," not "does it match a banned pattern" —
would a person SAY it. If you cannot hear a human saying the sentence, it
fails, whether or not any catalogued class matches. The catalogue below exists
to help you find such sentences and to name the cure; it is never the boundary
of the offense. A pass that runs every grep and skips this question is not a
lint.**

This skill improves clarity and honesty. It is not a tool for concealing AI
involvement: disclose AI assistance as your venue requires; Section E applies
to authorship statements too.

Quickly produced drafts, by people or by language models, share habits that careful readers distrust. A reader who has seen a lot of it flinches at the patterns below even when each sentence is individually fine. Run this as a dedicated pass — never assume a draft is clean because it "reads okay." Read every paragraph as if aloud; anything that sounds like a press release, a chatbot, or a social-media post gets rewritten in plain, concrete language.

**Two hard truths:**
1. **One pass is never enough.** These tells regenerate every time the text is rewritten. Scrub, then scrub again with fresh eyes, paying special attention to the opening sentence, every subheading, and every closing sentence — that is where they hide.
2. **The honesty tells (Section E) matter most.** A clunky sentence is cosmetic. A fabricated number, an inflated claim, or a mislabeled source is a lie. Hunt those first.

---

## A. Banned / suspect vocabulary

If one of these appears, it is almost always wrong. Delete or replace with a plain, specific word.

**Hype nouns/verbs:** delve, tapestry, realm, testament, underscore, leverage, unlock, unleash, navigate (figuratively), foster, embark, journey, showcase (as verb), spearhead, harness *the power of*, supercharge.
**Marketing adjectives:** seamless, robust, cutting-edge, game-changing, revolutionary, transformative, groundbreaking, multifaceted, intricate, vibrant, profound, rich (figuratively), powerful (as filler), unprecedented.
**Set phrases:** "harness the power of", "the world of", "dive into" / "deep dive", "at the forefront", "pushing the boundaries", "a paradigm shift", "the beauty of", "stands as", "serves as a testament", "a beacon of", "plays a vital/crucial/pivotal role", "boasts", "a treasure trove", "in today's world", "ever-evolving", "rapidly evolving", "needless to say", "at the end of the day", "simply put", "it goes without saying".
**Weasel openers:** "It's worth noting that", "It's important to note", "It is worth mentioning", "Notably,", "Importantly," (when it adds nothing), "Make no mistake".
**Summary throat-clearing:** "In conclusion", "In summary", "Ultimately,", "All in all", "To sum up".

*Allowed-in-context exceptions:* a word used literally (a software harness, a physical journey) or as a genuine technical term. The ban is on the cliché use, not the real one. **The defined-in-document exception:** a suspect token the document itself formally defines ("we call a value *certified* when …") is earned vocabulary from the definition onward — demote the hit to a note and check that the definition really exists and precedes the uses.

## A2. Metaphor and register classes (each with its cure)

**Commerce metaphors for information/evidence:** "the constants price the question", "a menu of methods", "what this buys", "cost" for anything other than literal compute time or literal sample size. *Cure:* state the actual quantity — "takes about 3 million samples" is fine; "the constants price the question" is not.

**Vague elevation metaphors:** "one floor up", "one level up", "one rung above", "the mathematical ladder", and kin. *Cure:* name the concrete thing — the class, or the actual dimension/order count ("the genus-two case, one step above genus one"). A *named, literal* ladder with real rungs stays allowed.

**Vague locative abstractions:** "the places where that stops are known precisely", "the point at which X breaks down", "on both sides of that boundary", "where the field currently stands" — geography metaphors standing in for specific objects. The tell: a WHERE-word (places, point, boundary, side, landscape, territory) carrying a claim about specific objects. *Cure:* name the objects — "exactly two cases are known to require more". A literal boundary (a physical region, an integration domain) is fine.

**"The field says" over-attribution:** "when the field says", "the field declared it impossible", "the field stopped trying" — generalizing one paper's or one group's statement to an entire discipline. Both a tone tell (gotcha framing toward likely referees) and an honesty tell (an attribution a source check refutes). *Cure:* attribute to the actual source, quoted or named ("Smith et al. call it 'impossible to evaluate directly'"), or scope to the actual subcommunity. If you cannot name who says it, the sentence is not ready.

**Capability-fanfare openers:** "the two theories can finally be compared", "X makes it possible to Y", "this opens the door to" — announcing that an act has become possible instead of performing it. *Cure:* do the thing — "We compare the prediction with the archival data." If the document doesn't do it, it's future work, stated as an open item, not fanfare.

**Paragraph-opening anaphora:** a new paragraph must not open on an unanchored pronoun or deictic — "We now cross it", "This changes the picture", "That is the subject of...", "It follows that..." as paragraph OPENERS force the reader back across the break to find the referent, and read as machine segues. Within a paragraph anaphora is fine. *Cure:* restate the noun. Doubly banned when combined with journey-geography verbs (cross, move to, turn to).

**Dev-subculture vocabulary in science prose:** footgun, moat, "has landed"/"lands" for results, happy path, escape hatch, guardrail (figurative), dogfood(ing), greenfield, bikeshed, yak-shaving — anything from the coding-agent/devops subculture. *The test:* would the author have used this word in a scientific paper before working with coding agents? *Cure:* ordinary English — trap, pitfall, hazard, failure mode, checker, wall, "is complete".

## A3. Agentless prose (the class the pattern lists do not catch)

Sentences that are grammatical, contain no banned vocabulary, and still read as machine/report prose because they dodge human agency or decorate structure.

**A3.1 — Abstract-agent constructions.** An inanimate abstraction performs a human verb: "The literature attaches a definite expectation to this coefficient"; "the record shows", "the analysis produced", "the section supplies", "the data argues". *Cure:* give the sentence a real subject — the people, or the plain fact: "There was every reason to expect a closed form"; "Smith and Jones showed"; "We find". **The person-subject test:** could you replace the abstract subject with a person's name and keep the verb? If not, the verb is borrowed and the sentence is fake.

**A3.1b — Pipeline vocabulary in scientific prose.** Software/devops register describing mathematics or science marks the text as machine-written. Banned on sight, each with its cure:

| banned | cure |
|---|---|
| downstream / upstream | "later results", "no later result depends on it", "the input to" |
| pipeline (for a derivation) | "the calculation", "the chain of arguments", "the method" |
| workflow | "procedure", "method" |
| hand off / handoff | "pass to", "becomes the input of" |
| flag (verb, no literal flag) | "note", "point out", "record" |
| surface (verb) | "reveal", "bring out", "expose" |
| ship / shipped (for results) | "publish", "include", "accompany the paper" |
| deploy | "apply", "use" |
| end-to-end | "complete", "from the definition onward" |
| artifact (for a result/file) | "record", "table", "computed data" |
| gate / gating (no named gate) | "check", "test", "criterion" |
| sanity check | "consistency check" |
| edge case | "degenerate case", "boundary case" |
| toolchain / tooling / stack | name the actual tools |
| bandwidth / throughput (figurative) | say the actual resource |
| iterate on (a draft/idea) | "revise", "refine" (mathematical iteration is fine) |
| blocker / pain point | "obstruction", "the difficulty" |
| load-bearing (figurative) | "essential", "the argument depends on it" |
| lane | "line of work", or name the actual activity |
| closed (completion status) | "complete", "entirely" |
| byte-identical / byte-for-byte (for exact values) | "exactly equal", "identical" — unless a literal byte comparison of files is the check, stated once |
| fail-closed / production use | "validated on cases with known answers before being applied to the real data" |
| status enums pasted verbatim (GO/NO-GO, not-gradeable-with-reason) | plain-English gloss at the definitional site, then use the defined term |

Example fixes: "nothing downstream rests on the fit" → "The fit plays no further role." "the derivation artifacts ship in the release bundle" → "the derivation records are included with the paper."
Exemption: a paper ABOUT software may use these words for the software itself (a real pipeline, a real workflow) — never for the mathematics.

**A3.2 — Contorted agentless idioms.** Constructions that twist to avoid saying who did what: "The program is named by its own titles", "admits a reading as", "attaches to", "is captured by the observation that". *Cure:* subject–verb–object with real actors.

**A3.3 — Decorated structural labels.** Run-in labels, paragraph headers, or list leads with relative clauses or editorial riders: "The geometry that explains it.", "The method, stated honestly", any "The X that Y" label; also the "Noun, participle" status rider ("The mechanism, proved"). *Cure:* labels are plain noun phrases, four words or fewer — "The theorem." — and the explanatory work moves into the paragraph's first sentence.

**A3.4 — The colleague test (mandatory, separate pass).** After the pattern hunt, run a SEPARATE pass reading as a senior person in the target field and venue: for each sentence, would that person write it? Hesitation = rewrite as subject-verb-object with a human or concrete subject. This is a different failure axis from the tell lists; pattern-matching the lists does not perform this test, and a pass that skips it WILL publish agentless prose.

---

## B. Banned sentence structures (the high-value targets)

**B1 — Negate-then-pivot ("not X, but Y" / "X, not Y" / "not X; it Y").** The single most common tell. Includes "It's not just X, it's Y", "is a feature, not a flaw", "It does not compute... it constrains". *Fix:* state the positive directly and drop the negated half. Keep at most one such construction in a whole piece, and only if the contrast is load-bearing.

**B2 — Cleft and pseudo-cleft ("It is X that…", "What … is …", "X is what …", "is exactly what/where …").** *Fix:* convert to a plain active sentence: "What carries over is the method" → "The method carries over." Three cleft sub-types that hide and must be hunted specifically:
- **Existential-there cleft:** "There is/are X … (that/who/and it is) …" — wordy throat-clearing that buries the subject. "There are many physicists who believe…" → "Many physicists believe…". Start with the real subject.
- **"it is the one/the thing/the reason …" tail**, often *mid-sentence after "and"* (clefts are not only sentence-openers — scan inside sentences too): "…, and that is what makes it work" → fold into a direct clause.
- **"what \<verb\>s … is …" with a non-"the" completion** — greps for "what … is the" miss clefts whose complement is a pronoun or possessive: "what survives of the fit is its output". Hunt ANY "what survives/remains/emerges/follows/carries/changes/works/matters … is …". Also its cousin, the **trailing-apposition flourish** — a comma tail describing the *document's* relationship to the object ("…, now the subject of a theorem") rather than the object itself. Fix both by stating the fact.
- **Specificational abstract-noun copula:** "The difference/reason/point/upshot is whether/that/how …" — a cleft with the wh-word moved into an abstract noun subject. The abstract noun adds nothing; the wh-clause is the content — let it modify the actual statement. Variants that evade greps: an interposed modifier ("The question for this note is whether…"), and the verbless colon form ("The answer to whether X: Y").

**B3 — "X changes one thing, and the one thing matters."** Fake profundity: assert something does one important thing, then declare that thing important. *Fix:* cut the self-referential second clause; just say what it does.

**B4 — Filler-emphasis flags** ("worth noting/savoring", "the key is", "what matters is") and enumerative meta-prose — a sentence whose only content is a count or a structure announcement ("Our result is then two things.", "Two points are worth making."). *Fix:* delete the flag and lead with the content; fold the count into the first content sentence.

**B4b — Participle-hedge stacks.** Two or more coordinated past participles, each carrying its own epistemic rider, in one clause: "proved modulo one lemma and validated on independent routes". Grammatical, technical, and machine to the ear — a person states one epistemic claim per clause. No pattern fires on it; hunt it by reading status sentences aloud.

**B4c — Announced significance.** Telling the reader a result is deep instead of showing it: "…and its anatomy is the deeper finding", "it is worth naming", "X is the real finding". *Fix:* delete the announcement — the demonstration follows anyway.

**B5 — "From X to Y," openers** ("From quarks to galaxies, …"). *Fix:* rewrite without the frame.

**B6 — Rhetorical-question-then-answer as a paragraph engine.** One per piece, maximum; zero in a research paper. Hook-question openers and hook-question titles are banned outright.

**B7 — "Imagine …" openers and "Enter [X]" reveals.** *Fix:* introduce the thing by name and what it does.

**B8 — Abstraction-labeling and structure narration.** "This is X in its purest form", "That number organizes the rest of the paper", "this section is the ledger". *Cure:* state what the object MEANS, not what it does to the document. Sibling: layout self-justification ("Itemized, because a grid is easy to scroll past") — the reader never needs the design defended.

**B9 — Aphorism-fragment codas.** Verbless slogan fragments as paragraph enders: "One channel, two symptoms." / "Two results, one mechanism." The content is always already in the sentence before. *Cure:* delete; if the identity needs stating, state it as a plain sentence with a verb. Siblings: the paired-gerund identity epigram ("doing X and doing Y are the same event"), vague-antecedent proof claims ("the paper proves it" — you prove statements, not causes; name the statements), compressed apposition ("at a rate the paper bounds" — give the fact its own clause), and paradox inversion ("manufactures X out of its own Y" — state the plain causal fact).

**B10 — Unhedged "the first X" flourish.** A first-claim is a factual claim: either pin it to a source and hedge ("to our knowledge, the first…") or cut it — usually the sentence works without it. One hedged first per document, maximum.

**B11 — Apposition-gloss instead of plain nouns.** A technical noun phrase glossed by a clever compressed apposition that names nothing: "the failures sit in the inference layer, the part the domain argues with". *Test:* from the sentence alone, can the reader list the concrete objects? If not, the gloss is decoration. These pass a read-aloud check — hunt them as a separate pass: for every apposition, ask what nouns it is hiding.

**B12 — Fancy phrasing instead of saying it.** "That asymmetry is where the story starts", "becomes a question with an answer", "the least of what this opens". Each performs instead of stating. *Cure:* write the sentence you would say to a colleague across a desk. If a metaphor spans more than one sentence it has become a frame — kill the frame, keep the facts.

**B13 — Stakes by pointer / reference without referent.** Reporting that a conclusion changed without saying what it was about: "reversing that part of the paper's story", "two of the source's headline claims lose support". The reader has not memorized the source. *Cure:* science forward — open with the real-world question in plain words, and give every moved number its real-world meaning in the same sentence.

**B14 — The two-beat echo.** A sentence repeating its verb or frame for cadence: "X fails, and it fails differently." / "It works, and it works everywhere." The second beat exists for rhythm, not information; treat verb-echo across a comma/conjunction as guilty by default. *Cure:* state the two facts plainly with their content. MECHANICAL SWEEP: flag every sentence where the same verb lemma appears twice joined by ", and" / "; " / "— and".

**B15 — The repeated flourish (document-scale; a per-sentence read cannot see it).** The same epigram, verdict sentence, caveat couplet, or caption formula deployed twice or more across a document: a conclusion re-asserted in near-identical words after each block of evidence; a hedge stamped verbatim in the preamble, three captions, and the close ("preliminary, a proof of principle" in the preamble, three captions, and the close); a priority claim ("the first X") told in the introduction, a caption, and three sections; consecutive captions on one superlative template ("The A, the best-described of the three…" / "The B, the most structured of the three…"); an abstract sentence recycled near-verbatim into the introduction. One instance is voice; repetition is assembly. *Cure:* give the statement its full form ONCE at the site that owns it, keep any per-figure stamp policy, and reduce the rest to a plain reference or delete. *Keep-boundary:* a scope qualifier deliberately attached to every conditional number is discipline, not a tic — before bulk-trimming an apparent chorus, check whether each instance carries its own fact; if it does, it stays. Siblings: the counted-opener template run ("Two gaps remain." / "Two conclusions follow." / "Two checks are independent…" chapter after chapter — keep at most one, fold the rest into ordinary prose) and the dramatic-opener chain (a narrative section whose paragraphs all open on a punchy sub-8-word beat: "First contact went badly." / "The reckoning came." — keep at most two).

**B16 — Credential display (validation vocabulary worn as a badge).** Method-integrity vocabulary used as a self-conferred credential rather than a defined term: certified, verified, validated, pre-registered, pre-committed, frozen protocol, blind, held-out, fail-closed, audit-grade — sprinkled through results without the document ever saying what operation confers the label. Readers experience this as protesting too much, and it buries the actual guarantee. *Cure:* define the term once, concretely, at first heavy use ("a value is *certified* to n digits when two independent evaluations agree to n digits"), after which the register is earned — or replace each use with the concrete fact ("agrees with an independent evaluation to 30 digits"). Procedural credentials ("under a frozen, preregistered protocol") are methods material, never selling points. Same family: integrity oaths stapled to facts that carry themselves — "the miss is declared, not waived", "the limitation is recorded", "disclosed at full prominence", "we note, against any suspicion of selection, that…", "right rather than convenient", "stated, not patched". The disclosure IS the preceding sentence; delete the oath. And self-congratulating checks ("the controls did their job") — state each check's outcome instead.

**B17 — Register saturation (one evocative word colonizing the document).** A single borrowed register noun or verb doing service everywhere: verdict (courtroom), referee, interrogate, campaign, battle-tested (martial), price/pays/buys (commerce), climbs (journey). One or two uses may be voice; ten is a costume. *Sweep:* count occurrences of each evocative register word; past ~4–5, translate all but the one or two load-bearing uses to the plain word (answer, result, check, cost, grows). Related: personified apparatus with communicative or judicial verbs — "the control run caught one genuine event", "the instrument proves itself", "the criterion decides", "the rule fired" — instruments and criteria are used and applied by people; recast with the mechanism ("a repeat under the control configuration revealed…") or a we-subject. Mathematical objects with natural dynamics survive (maxima split, chains converge).

---

## C. Rhythm and paragraph shape

- **C1 — Rule-of-three cadence.** The default LLM rhythm is the manufactured triple ("faster, cheaper, and more reliable"). A genuine enumeration of three real things is fine; if two of the three are padding, cut.
- **C2 — Restatement codas.** A paragraph's last sentence re-saying the paragraph in punchier words. Delete, or end on something that adds or turns forward.
- **C3 — Sentence-opening sameness.** Every sentence starting "The …" or "It …". Vary openings and lengths. Also: no epigram stacking (two flourishes back to back).
- **C4 — Em-dash stuffing.** Ration hard: at most one em-dash in an entire document. Convert asides to parentheses or commas, connective dashes to colons or new sentences.
- **C5 — Fronted-inversion openers.** Locative inversion as a dramatic pivot — "Behind the hardness sits a structural question", "One level above X sits Y" — especially as a section-opener template reused across sections. Un-invert all but at most one: "The hardness raises a structural question". Kin: the quiz-show colon ("The answer: X." — a verbless drumroll; write "The answer is that X") and colon-ended announcers ("Zero cases failed:" — the sub-8-word announcer scan covers ':' endings, not just '.').
- **C6 — Superlative self-ranking.** The document grading its own contents: "the sharpest structural question", "the strongest control", "the sharpest single fact in the data set is…" — a ranking epithet plus a specificational copula introducing evidence that speaks for itself. State the fact directly; if a ranking template repeats ("the sharpest X" twice), vary or drop one.

## D. Formatting tells

Random mid-paragraph bold; stacked hype adjectives; title clichés ("Unlocking…", "A Deep Dive into…", colon-gerund subtitles, hook-question titles); emoji; bulleted lists where prose belongs.

---

## E. Honesty tells (most important — integrity, not style)

- **E1 — Fabricated specificity.** Inventing numbers, counts, or dates and presenting them as data. Use only quantities with a real source; if something is an estimate, say so or cut it. Prefer a smaller verified claim to a bigger guessed one.
- **E2 — Importance inflation.** Claiming something is needed or matters more than it does. Claim only what is true — "at the frontier of what is computable", not "what the field needs".
- **E3 — Provenance errors.** Mislabeling who built, wrote, or discovered something. Verify against the actual repo/paper, not memory.
- **E4 — Result over-claim.** Rounding a partial or unverified result up to "done". Report the true status; never imply a check passed that didn't.
- **E5 — Confident fuzziness.** Stating a contested or approximate fact (a "first", a record, a date) flatly. Pin it against a source, or hedge precisely, never vaguely.
- **E6 — Enclosure and quotation integrity.** (a) Certified intervals round OUTWARD, always: lower endpoints down, upper endpoints up; a certified lower bound may only be rounded DOWN. (b) Quotation marks require a verbatim receipt — a fair paraphrase in quotes is a provenance error. (c) Error-bound and residual summaries may only round in the CONSERVATIVE direction (a 1.06×10⁻⁷ agreement is NOT "10⁻⁷"); trace every order-of-magnitude summary to its source value and check the rounding direction.

## N. Number discipline and cross-surface consistency

Every number appears on several surfaces — body text, table, caption, figure label, abstract — and each pair of surfaces is a place for a silent contradiction. These classes are mechanical; sweep them, don't trust the eye.

- **N1 — Rounding direction on measured counts.** Never round a measured digit/precision count UP: a measured 23.85 verified digits prints as 23, not 24. Achievement numbers round toward the weaker claim, always.
- **N2 — Subtraction-consistent display.** Numbers a reader will subtract must round consistently: 41.2 and 3.9 support "a 37-digit gap"; flooring each independently (41, 3) makes the printed arithmetic false. Same law for decomposition sums: rounded columns must recompose to the rounded total, or the display precision changes.
- **N3 — Every N/N and N-of-M carries its unit.** "812/812 exact" — entries, columns, rows, or members? A count whose noun comes from a different surface than its number is wrong until checked against the source's own definition. Sibling: a compressed count whose gloss names the wrong object ("k=6 collections" when the 6 are histogram cells).
- **N4 — The display-tie.** A value landing exactly on a rounding tie (141/400 = 0.3525) prints differently under float formatting (35.2 — float64 stores it just below the tie) and half-up display (35.3), so a generated label and the text silently disagree on the same number. Compute display labels from integer counts with exact half-up decimal arithmetic, never from the float.
- **N5 — Second-generation rounding.** A ratio or difference of already-rounded values (0.172/0.126 → 1.37) differs from the unrounded computation (1.362). Quote the source record's number verbatim; never "correct" a citable record by re-deriving from displayed values. Likewise a z-score or ratio that "fails" recomputation from displayed inputs may be exact from unrounded ones — say which convention computes it.
- **N6 — A decomposition that doesn't sum names its boundary.** When printed parts miss their printed total, the usual cause is two different boundaries in one analysis (a selection window cut by date, labels assigned by a different scheme), not a stale number. Find the boundary mismatch and state it; don't nudge a number to force the sum.
- **N7 — Non-nested denominators.** Two filters can differ by a NET count (4,201 kept vs 4,178 kept, overlap 3,900): "23 fewer" is true, "23 removed" is false. Check nesting before writing any subset clause.
- **N8 — Counterintuitive-direction numbers get a mechanism clause.** A correct number that moves the "wrong" way (power falling as the sample doubles) reads as a typo. Verify it, then attach the half-sentence mechanism at every site where it prints.
- **N9 — Two true numbers, one false parenthesis.** Two statistics sharing a parenthesis ("p=0.005; fifteen standard deviations above the mean") invite the reader to compose them into a claim neither supports. Each names its own provenance, or they separate.
- **N10 — Modals are part of the number.** "the estimate can be 1.08 times the bound" compressed to "is 1.08 times the bound" turns a possibility into a determination. When compressing or restating a claim, check the modal (can-be / is / must-be) as carefully as the numeral.
- **N11 — One symbol, one object.** Run a symbol census on collision-prone letters: the same letter as a coefficient in one section and a curve, a matrix, or a radius in another actively misleads a reader tracking it — worst when both senses appear in one argument. Rename the cheaper instance and sweep. Same class in words: one term used in a technical and an ordinary sense in the same passage — gloss or rename at first use.
- **N12 — Claim-bearing connective prose.** Relative clauses silently attribute checkable facts ("the trend that their best-fit model carries") — consistency passes must cover the connective prose around numbers, not just the numerals.
- **N13 — Identifier integrity, both directions.** A correct-looking identifier can be wrong and a wrong-looking one correct: registries migrate prefixes, so a DOI with an unfamiliar prefix may be the real one while the "canonical" form no longer resolves. Never normalize an identifier to the familiar form without resolving BOTH candidates; when the odd one wins, leave a dated do-not-fix note so a later pass doesn't undo it. Bare integers where a citation belongs may be a citation-command misfire (a numeric-style \citealp emits "(cf. 9)") — check the bibliography rendering before suspecting a hand-typed number.

---

## F. The parse and composition pass — run BEFORE the tell hunt

The tell catalogue cannot catch what it does not contain. Before any pattern hunt, read for MEANING, sentence by sentence:

1. **Grammar.** Subject and finite verb present? Topic-position fragments ("First, a change to the picture of X.") are ungrammatical, not style.
2. **Antecedent resolution (hard rule).** Every pronoun and deictic — it, this, that, "the effect", "the answer" — must resolve to ONE unambiguous referent within the previous two sentences. Section-opening deictics must survive the page turn.
3. **False agency.** No object doing what it cannot do: "the dataset returns an answer" (the fit run on it produces the answer), "the data want". MECHANICAL SWEEP: grep every inanimate-subject + agentive-verb pair — subjects like record, catalog, dataset, table, curve, model, paper, section crossed with verbs like returns, answers, tells, knows, decides, hides, insists, remembers, wants, admits. Every hit is guilty until the sentence proves the verb literal.
4. **Internal consistency.** Any sentence that APPEARS to contradict another claim anywhere in the document fails, even when both are true — put the reconciliation on the page at the first occurrence.
5. **The document-about-itself ban.** Section and paragraph openers make a claim about the WORLD, never about the document: "This section presents…", "We now turn to…", "Having established X, we…" are document furniture. The one licensed home for signposting is the introduction's roadmap paragraph.
6. **No one-sentence paragraphs.** A paragraph is a developed thought: state, support, connect. Runs of thin 2–3 sentence paragraphs fail the same way; merge thin neighbors.
7. **The skimming-reader test.** Extract every paragraph's FIRST SENTENCE and read each in isolation. Each must name its subject with full nouns and stand alone; the fast reader never traces back.
8. **The continuous read.** For any document over a few pages, one cold read cover to cover IN ORDER after the per-section passes — the only way cross-boundary reference and cross-section consistency failures get caught.
9. **Render integrity (lint the OUTPUT, not the source).** Read the rendered document, not the source file: a source-side edit can silently eat the following live text (a comment or edit tail swallowing the next sentence), leaving a subjectless fragment, a lowercase sentence start, or an unbalanced parenthesis in the render that the source read never shows. When a rendered sentence is garbled, check the adjacent comments/edit markers for the swallowed tail FIRST and restore it verbatim — never rewrite a broken sentence from memory.
10. **The twin-splice sweep.** Two identical comma-splices in one document mean an unproofed edit wave, not typos — where one sentence boundary was lost, others from the same wave usually exist. Scan the render for ", [A-Z]" after a closing parenthesis or a long clause and audit every hit.
11. **Records are tenseless.** Archival/print prose carries no lab-log deixis: "as of today", "enters no check today", a heading stamped with a run date. Chronology belongs in logs and version history, not the document's claims.

Three sharpened kin: **process-abstraction agency** ("Sampling gives no warning", "optimization promises" — process nouns never take communicative verbs; concrete objects with natural dynamics survive: maxima split, chains converge); **staccato verdict-beats** (a <8-word declarative re-asserting what the evidence just showed, or announcing the next act's theme — drama typography, usually hiding an agency defect; drop, don't rephrase); **announcement sentences** ("We give a theory of when this happens" — a vague promise with no content; cut and let the concrete contribution sentences carry).

## G. The scrub procedure

1. **Read it aloud, sentence by sentence.** Flag anything that sounds like marketing, a chatbot, or a press release.
2. **Run the parse/composition pass (F) first**, then grep the vocabulary (A) and structures (B), then run the A3 greps and the A3.4 colleague test as their own pass.
3. **Check openings and closings.** First sentence, every subheading, every paragraph's last sentence — the densest hiding spots.
4. **Read the abstract as someone who has read nothing else.** Any internal name used without an antecedent is a tell (the paper talking to itself). Run the colleague test in the abstract's register: the colleague has not read the paper.
5. **Dictated text is not exempt.** Author-supplied sketches are content specifications, not finished prose — render and lint them like everything else.
6. **Lint the linter's output.** Fixes are new prose and regenerate tells. Whoever rewrites a sentence cannot be the last to review it: sweep the DIFF of every fix pass with different eyes.
7. **Run the honesty pass (E) and the number pass (N) separately and first in priority.** Verify every number, name, date, and attribution; run the cross-surface checks (body vs table vs caption vs figure label) on the rendered text.
8. **Root-cause every external catch.** When a reader flags a sentence that passed this skill, make TWO edits: cure the sentence, AND add the pattern here with the caught quote as its type specimen. A miss without a new entry is a repeat waiting.
8b. **Verify before "fixing."** A finding is a hypothesis, not a verdict. An identical value in two roles can be a coincidence with both sides correct; an odd-looking identifier can be the real one (N13); a comment in the source stating a premise ("the source never asserts X") can be stale — comments are provenance, not law: check the cited source before obeying, and when the premise is false, supersede the comment with a dated correction. Freeze any number you cannot verify rather than "improving" it.
8c. **Respect quoted and generated material.** Locate every verbatim-quoted span (block quotes of records, licensed excerpts) BEFORE editing — a cure that lands inside quoted material gets reverted, not defended; the editable surface is the surrounding prose. Generated tables/figures/captions are cured in their GENERATOR and regenerated, never hand-edited in the output; verify the regeneration changed only what the cure intended.
9. **Fixed-point loop for ship-critical text:** lint→fix→fresh-lint until a fresh pass returns zero findings. Findings cite a named rule (no taste-only findings); prior deliberate cures are protected from re-styling; the fixer replaces verbatim and never re-flows. Never report "linted to stability" as a quality claim — a fixed point certifies only that the sweep you ran finds nothing more; report what was checked.

Final test: *would a sharp human editor with no patience for machine-sounding prose wince at any sentence here?* If yes, it is not done.

---

## Quick grep sweep (starting point, not exhaustive)

```
grep -inE "delve|tapestry|realm|testament|underscore|leverage|unlock|unleash|seamless|robust|cutting-edge|game.?chang|revolutioni|paradigm|dive into|deep dive|the world of|ever-evolving|in today's world|treasure trove|boasts|a beacon|stands as|the beauty of" FILE
grep -inE "one floor|floor up|one rung|rung above|one level up|mathematical ladder|footgun|\bmoat\b|has landed|happy path|escape hatch|guardrail|dogfood|greenfield|bikeshed|yak.shav" FILE
grep -inE "downstream|upstream|pipeline|workflow|hand.?off|end-to-end|sanity check|edge case|toolchain|tooling|\bship(s|ped)?\b|\bdeploy|iterate on|blocker|pain point|load-bearing" FILE
grep -inE "the field (says|said|declared|decided|thinks|believes|calls|stopped|gave up)|field's (own )?verdict" FILE
grep -inE "not just|is a feature, not|not a .* but|; it [a-z]|is exactly wh|is what [a-z]+s |what .* is the|worth noting|worth savoring|the key is|what matters is|in conclusion|in summary|ultimately," FILE
grep -inE "what (survives|remains|emerges|follows|carries|changes|matters|works|counts)[^.?!]* is |, now (the|a|its) [a-z]+ (of|for)|now the subject" FILE
grep -inE "The (difference|reason|point|answer|upshot|issue|trouble|question|key|trick|surprise) (is|was) (whether|that|what|how|why|in )" FILE
grep -inE "There (is|are|was|were) [a-z]|, and it is the |, and that is wh|it is the (one|thing|reason)" FILE
grep -inE "the (literature|record|analysis|program|survey|data|section|study) (attaches|shows|produced|reveals|supplies|presents|argues|records)" FILE
grep -inE "^[A-Z][^.!?]{3,60}\.$|(One|Two|Three) [a-z]+, (one|two|three) [a-z]+\.|the (first|only) [a-z-]+ (stack|tool|pipeline|method|system)|proves (it|this|that)\b" FILE
grep -inE ", (proved|adjudicated|stated)[}.]|deeper finding|is the point:|worth naming" FILE
grep -inE "is where the story|the least of what|a question with an answer|where it bites|becomes visible at all|the (paper|study|author)'?s? (story|central question|narrative)" FILE
grep -inE "\b(sampling|optimization|the analysis|the procedure|the pipeline) (gives|tells|warns|promises|assures)|We (give|present|offer|provide) a (theory|framework|picture|account) of" FILE
grep -inE "\[[0-9]+\.[0-9]+, ?[0-9]+\.[0-9]+\]" FILE   # certified intervals: endpoints must round OUTWARD vs source
grep -icE "\bverdict|\breferee|\binterrogat|\bprice[ds]?\b|\bcampaign" FILE   # register saturation: >4 hits on one register word = B17 sweep
grep -inE "byte.for.byte|byte-identical|byte-level|fail-closed|pre-committed|pre-register|frozen protocol|calibrated blind" FILE
grep -inE "declared, not|not waived|is recorded\.|disclosed (as such|in full)|against any suspicion|rather than (convenient|bury)|did (its|their) job" FILE
grep -inE "proof of principle|to our knowledge" FILE   # count the hits: repeated hedge stamps and priority claims = B15
grep -inE "(Behind|Beneath|Atop|Above) the [a-z]+ (sits|lies|stands)|The (sharpest|strongest|deepest|cleanest) [a-z]+" FILE
grep -inE "^(One|Two|Three|Four) [a-z]+ (remain|follow|complete|stand)[s]?\.|The answer: " FILE
```
Treat every hit as guilty until proven innocent. Clefts hide *inside* sentences after "and/but", not only at sentence start — read for them; do not rely on grep alone. The document-scale classes (B15 repetition, B17 saturation, N cross-surface consistency) are invisible to any per-sentence read — run their counts and cross-surface checks as their own pass on the RENDERED text.

## Parse-pass 12: broken sentences from comment edits (the swallow class)

The single most productive TRUE-DEFECT check on any LLM-edited document: **sweep the
rendered artifact for lowercase-after-period**. When an editing pass inserts a comment
(or any annotation) before existing text, the following sentence's head is routinely
absorbed into the comment or dropped outright — the render then reads "...previous
sentence. orphaned lowercase tail..." and every per-sentence prose read misses it,
because readers repair broken syntax unconsciously.

Mechanics:
- Extract text from the RENDERED artifact (not the source) and scan for `. [a-z]{3,}`
  after filtering abbreviations (al., eq., cf., i.e., e.g., vs., Fig., Sec., ref., ...).
- Expect heavy noise: table cells, figure interleaves, lowercase-styled product names,
  hyphenation, and ligature loss (extraction can render "fits" as "ts" and "chiefly" as
  "chiey" — a candidate that looks broken may be a ligature artifact, and a cure you
  can't find in the render may be hiding behind one). Verify every candidate against the
  SOURCE before calling it real: a true break shows a comment line whose tail is orphaned
  prose, or a head that is simply gone.
- Editing hygiene that prevents the class: when a replacement inserts a comment before
  existing text, include the following sentence head in BOTH the old and new strings, and
  never end a replacement on a comment line. Never let a cleanup pass delete a comment
  line whose tail is prose — that is where eaten heads live.
- Recovery oracle: the version history of the rendered artifact. Walk back to the newest
  version where the sentence is whole and restore the head verbatim; do not paraphrase a
  head you can recover exactly.
- Special hazard: a comment inserted inside a brace-delimited argument (a caption, a
  footnote) can swallow the closing brace and break the build far from the edit. Keep
  comments outside argument braces.

Two build-layer traps that masquerade as prose problems: (a) bibliography databases do
not support in-entry comment syntax, and some parse annotation characters even in the
junk between entries — keep dated notes above entries and free of special characters;
(b) a successful build exit code does not guarantee the render picked up a regenerated
bibliography — verify the RENDERED text carries the change, and force a full rebuild
when it doesn't.

**Sources and acknowledgments.** The catalogue was compiled from our own editing
record, but the vocabulary in Section A overlaps heavily with the public
studies of LLM "excess vocabulary" by Kobak, González-Márquez, Horvát and Lause
(Sci. Adv. 11 (2025) eadt3813) and Liang et al. (arXiv:2403.07183, ICML 2024)
and with the community-maintained page Wikipedia:Signs of AI writing
(WikiProject AI Cleanup), which readers should treat as the better-documented
sources; the cures are the plain-style advice of Orwell ("Politics and the
English Language", 1946) and of Gopen and Swan ("The Science of Scientific
Writing", 1990), to whom most of Section B ultimately belongs.

---
