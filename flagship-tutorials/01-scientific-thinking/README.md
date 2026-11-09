# Scientific Thinking: From Observation to Explanation

**Status:** draft  
**Version:** 0.2.0  
**Audience:** curious learners; no specialist science background required  
**Estimated time:** 3–5 hours, plus optional follow-up investigation  
**Domains:** Cognitive Foundations; Evidence and Reality; Models and Principles; Creativity and Discovery  
**Central question:** How do we move from noticing a phenomenon to a defensible explanation—and then use that explanation to discover something new?

> A scientific explanation is not a confident story. It is a model constrained by evidence, explicit assumptions, and tests that could prove it wrong.

## 1. What you will learn

By the end, you should be able to:

1. distinguish an observation from an interpretation, hypothesis, model, and conclusion;
2. turn a broad curiosity into a precise, investigable question;
3. define variables and design a fair, repeatable test;
4. collect and inspect data, including uncertainty and possible sources of error;
5. construct a simple mathematical model and state its assumptions;
6. compare predictions with observations without hiding inconvenient results;
7. use an AI agent as a research assistant while independently checking its work;
8. transfer the process to a new question and explain what remains unknown.

You do not need to memorize every scientific fact. You do need enough foundational knowledge to recognize what a claim means, what evidence would support it, and where an explanation may fail.

## 2. The inquiry cycle

Scientific work is not always linear. Researchers revisit earlier steps when new evidence exposes a weak assumption or a better question.

1. **Notice:** describe a phenomenon without prematurely explaining it.
2. **Question:** identify something specific that could be investigated.
3. **Operationalize:** define what will be changed, measured, and held constant.
4. **Hypothesize:** state a provisional explanation and a prediction.
5. **Design:** choose a test that can distinguish between plausible explanations.
6. **Observe:** collect data with enough context to interpret it.
7. **Analyze:** compare observations with predictions and quantify uncertainty where possible.
8. **Revise:** retain, narrow, or reject the explanation in light of the evidence.
9. **Communicate:** show the evidence, method, limitations, and reasoning.
10. **Create:** use the improved understanding to ask a new question or build something.

This is a reasoning framework, not a universal recipe. Historical sciences, observational astronomy, field ecology, and controlled laboratory experiments have different methods and constraints.

## 3. Case study: what determines a pendulum's period?

A pendulum is a useful first investigation because it is inexpensive, observable, and connected to a mathematical model.

### 3.1 Start with observation

Hang a small weight from a string and pull it slightly to one side. Release it without pushing. It swings repeatedly.

Write only what you can observe:

- The motion repeats.
- The time for one complete cycle appears fairly consistent.
- Changing the string length seems to change the timing.

Now separate interpretation from observation. "The longer string causes a longer period" is a hypothesis based on an observation, not the observation itself.

### 3.2 Form a precise question

A useful question is:

**How does the pendulum length affect the time for one complete oscillation when the release angle is small?**

This question identifies:
- independent variable: pendulum length, measured from the pivot to the center of the bob;
- dependent variable: period, the time for one complete back-and-forth cycle;
- controlled conditions: bob, pivot, release angle, release method, and measurement procedure.

A fair test changes the intended independent variable while keeping other relevant conditions as stable as practical.

### 3.3 State a hypothesis and prediction

Hypothesis:

> For small release angles, increasing the pendulum length increases its period.

A stronger hypothesis makes a quantitative prediction. The ideal simple-pendulum model predicts:

T = 2π√(L/g)

where:
- T is the period in seconds;
- L is the length in metres, measured from pivot to bob centre;
- g is gravitational acceleration, approximately 9.81 m/s² near Earth's surface.

The equation predicts that period is proportional to the square root of length. If length is multiplied by four, the predicted period doubles.

This is a model, not a law that applies under every condition. It assumes a point-like bob, a light inextensible string, negligible friction and air resistance, and a sufficiently small swing angle for the small-angle approximation. OpenStax derives this result from the small-angle approximation and describes the point-mass, light-string idealization; it notes that the approximation is accurate to within 1% for angles below about 15° [1]. The suggested 5–10° release range is deliberately more conservative.

### 3.4 Design the experiment

**Equipment**
- string and a small, compact weight;
- a secure pivot;
- ruler or measuring tape;
- stopwatch or phone timer;
- notebook or spreadsheet.

**Procedure**
1. Secure the pivot so it does not move.
2. Measure length from the pivot to the centre of the weight.
3. Use a small release angle, for example about 5–10 degrees.
4. Release without pushing.
5. Time 10 complete oscillations, not just one.
6. Divide the total time by 10 to estimate the period.
7. Repeat at least three times at the same length.
8. Repeat for several lengths, for example 0.25 m, 0.40 m, 0.55 m, and 0.70 m.
9. Record unexpected events, such as a collision, a moving pivot, or a missed count.

Timing multiple oscillations reduces the relative effect of stopwatch reaction time when the start/stop delay is small compared with the total timing interval. Repetition helps reveal variability; it does not automatically remove a consistent bias.

**Record enough detail for someone else to repeat the activity.** Alongside the table, record:
- bob shape, approximate size and material; string material; and how the pivot is secured;
- how length is measured (pivot to bob centre), and the ruler's smallest displayed increment;
- how the release angle is set, how the bob is released without a push, and the point/direction used to start and stop timing;
- timer type or app, displayed resolution, number of cycles per timing, and number of repeats;
- every raw trial time, any excluded trial and the reason for exclusion;
- formulas, rounding, graph axes and units, fitting method, and whether the fitted intercept was free or fixed;
- whether values are learner measurements, a published dataset, or simulated data.

Keep raw observations separate from calculated periods and fitted results. Do not silently delete inconvenient trials.

**Safety:** keep the weight small, secure the pivot, keep faces and fragile objects out of the swing path, and do not use an overhead fixture that may detach.

### 3.5 Record data transparently

Use a table like this. Do not fill missing measurements with guesses.

| Length (m) | Trial 1: 10 cycles (s) | Trial 2 (s) | Trial 3 (s) | Mean period (s) |
|---:|---:|---:|---:|---:|
| 0.25 | | | | |
| 0.40 | | | | |
| 0.55 | | | | |
| 0.70 | | | | |

Calculate each trial's period by dividing its 10-cycle time by 10. Calculate the mean period from the repeated period estimates.

If you cannot perform the experiment, you may use a published dataset or a clearly labeled simulated dataset to practice analysis. Never describe simulated or illustrative values as measurements you collected.

### 3.6 Analyze before explaining

Make a scatter plot of mean period T against length L. Then make a second plot of T² against L.

The model predicts:

T² = (4π²/g)L

So a plot of T² against L should be approximately a straight line through the origin under ideal conditions. Its slope is 4π²/g, allowing an estimate of g:

g = 4π² / slope

The slope has units s²/m, so the resulting estimate of g has units m/s². Record the regression method and whether an intercept was fitted; these choices affect the interpretation.

Before interpreting the slope, check:
- Are units consistent?
- Is length measured to the bob's centre?
- Is the swing angle small?
- Are repeated trials reasonably consistent?
- Are there outliers with documented causes?
- Does the fitted line show a systematic pattern in its residuals?

Do not force a line through the origin simply because the ideal equation predicts it. First inspect whether the intercept is consistent with measurement uncertainty and the experimental setup.

### 3.7 Interpret the result

A responsible conclusion has four parts:

1. **Finding:** what pattern does the data support?
2. **Evidence:** which measurements or plots support that statement?
3. **Model comparison:** how well does the prediction agree with the observations?
4. **Limitations:** what could explain disagreement, and what has not been tested?

Avoid saying "the experiment proves the formula." A finite experiment can support a model within tested conditions; it cannot establish that the model is universally true.

## 4. From data to knowledge: a worked reasoning example

Suppose a learner finds that a longer pendulum generally has a longer period. That observation is consistent with the model, but it does not by itself establish the square-root relationship.

The learner then plots T² against L. If the points approximately follow a straight line, the result is more specifically consistent with the model's prediction.

Even then, alternative explanations and measurement problems remain possible. For example:
- the length may have been measured to the bottom of the bob rather than its centre;
- the release angle may have varied with length;
- the pivot may have moved;
- the timing method may have introduced a consistent delay;
- air resistance and pivot friction may have affected the motion.

A useful scientific habit is to ask: **What result would make me change my mind?** If every possible outcome is interpreted as support, the hypothesis has not been tested meaningfully.

## 5. Uncertainty and honest measurement

Measurements are not exact. A ruler has finite resolution; a stopwatch depends on reaction time; the bob may not follow an ideal path.

Distinguish:
- **resolution:** the smallest increment an instrument displays;
- **repeatability:** how similar repeated measurements are under similar conditions;
- **random effect:** a source of trial-to-trial variation under similar conditions;
- **systematic effect:** a consistent influence that may bias results, such as measuring from the wrong reference point;
- **model limitation:** the idealized equation omits effects present in the real setup.

Do not treat *measurement error* and *measurement uncertainty* as synonyms. In formal metrology, uncertainty characterizes the dispersion of values that could reasonably be attributed to the measurand; the relationship between random/systematic effects and formal uncertainty components is not a simple one-to-one mapping [3]. This tutorial uses the terms qualitatively and does not claim a complete uncertainty budget.

Do not report more decimal places than the method supports. If the three trials differ noticeably, report the spread as well as the mean. If a systematic effect is suspected, explain how it might shift the result; taking more trials alone may not fix it.

## 6. Use an AI agent as a collaborator—not an authority

An agent can accelerate inquiry, but it can also produce fluent mistakes. Use it to widen your thinking and expose weaknesses, not to replace evidence.

### Task A — Generate competing explanations

Ask an agent:

> I am investigating how pendulum length affects period. Give me three plausible explanations or models, their assumptions, and one observation that could distinguish each. Separate established physics from speculation and provide sources for factual claims.

Your job:
- identify whether the explanations are genuinely different;
- check the sources and equations;
- reject explanations that do not make testable predictions.

### Task B — Audit the experimental design

Ask:

> Critique this pendulum experiment. Identify confounding variables, measurement errors, safety issues, and changes that would make the test more informative. Do not assume my procedure is correct.

Your job:
- decide which criticisms matter most;
- distinguish practical limitations from fatal flaws;
- revise the method and explain why.

### Task C — Verify an analysis

Give the agent your actual table and ask it to calculate periods, means, a T²-versus-L fit, units, and residuals.

Then independently verify at least:
- one period calculation;
- one mean;
- the fitted slope and its units;
- the conversion from slope to g;
- whether the data support the assumptions.

A script that runs successfully can still calculate the wrong quantity. An agent's confidence is not a quality check.

### Failure challenge

Ask the agent to review a deliberately flawed report in which the learner:
- times one swing only;
- changes both length and release angle;
- reports simulated values as experimental measurements;
- claims that agreement proves the model universally;
- omits units.

Can you identify every defect and explain its consequence?

## 7. Practice: test your understanding

Answer before consulting an agent.

**Classification check:** classify each statement as an observation/measurement, interpretation, hypothesis, model, or conclusion, and explain your choices:
- “The bob passes the centre mark on each swing.”
- “The measured mean period for this setup was 1.27 s.”
- “A longer string causes a longer period.”
- “The ideal model predicts T = 2π√(L/g).”
- “These measurements are consistent with the model over the lengths tested.”

Then answer the questions below.

1. A learner says, "The bob is heavier, so the pendulum must swing faster." What evidence or model would you use to evaluate the claim?
2. Why time 10 cycles rather than one?
3. Why measure length to the centre of the bob?
4. If the period doubles, what does the ideal model predict about the length?
5. Your data fit a straight line in T² versus L but the intercept is clearly nonzero. Give at least three possible explanations.
6. Why does repeating a measurement not necessarily remove systematic error?
7. What would count as evidence against the small-angle model in your setup?
8. Which parts of an agent-generated analysis must you verify independently?

### Suggested answers and reasoning

1. The ideal simple-pendulum model predicts no dependence on bob mass under its assumptions. Test mass while keeping length and release angle controlled; check whether the apparatus introduces mass-dependent effects.
2. Timing more cycles makes reaction-time error a smaller fraction of the total measured time.
3. The model defines length from the pivot to the bob's centre of mass; a different reference introduces systematic error.
4. Since T² is proportional to L, doubling T implies four times the length.
5. Possible causes include a length zero-offset, inconsistent pivot geometry, non-small angles, timing bias, or model limitations. The data and setup are needed to distinguish them.
6. Repetition can reduce uncertainty from random variation in an average, but a consistent bias remains.
7. Look for a systematic mismatch between measured periods and the small-angle prediction as the release angle increases, while controlling other variables.
8. Units, formulas, data selection, calculations, fitting assumptions, and interpretation.

These are example lines of reasoning, not a substitute for analyzing your own measurements.

## 8. Transfer challenge: investigate a new phenomenon

Choose one question:
- Does the cooling rate of hot water depend on the container material?
- How does the angle of a ramp affect the time a toy car takes to travel a fixed distance?
- How does the length of a paper helicopter's rotor affect its fall time?
- Does changing the spacing of identical obstacles alter the flow pattern in a simple water channel?

For your chosen question, produce a one-page investigation plan containing:
1. the precise question;
2. an observation that motivated it;
3. at least two competing hypotheses;
4. variables and operational definitions;
5. a test procedure and safety considerations;
6. a data table design;
7. a prediction that could be wrong;
8. likely sources of uncertainty;
9. what evidence would change your conclusion.

If a controlled experiment is not feasible, explain why and propose an observational or computational alternative with its limitations.

## 9. Creation challenge: improve the investigation

Go beyond repeating the known experiment. Propose one extension:
- measure how release angle changes the period;
- compare different bob shapes to investigate air resistance;
- estimate local gravitational acceleration and discuss the limits of the estimate;
- compare a physical pendulum with the simple-pendulum model;
- build a low-cost timing sensor and validate it against manual timing.

Your extension must identify what is new, what is already known, what evidence would validate the result, and what would count as failure.

Originality is not merely choosing an unusual topic. It means making a meaningful contribution and being honest about its scope.

## 10. Assessment rubric

Assess each dimension separately. A polished report is not enough.

### Outcome-to-evidence alignment

| Learning outcome | Required evidence in this tutorial |
|---|---|
| Distinguish observation, interpretation, hypothesis, model, and conclusion | Classification check above, with reasons for at least two classifications |
| Turn curiosity into a precise question | Transfer plan states a focused, investigable question |
| Define variables and design a fair, repeatable test | Investigation plan defines variables, operational measurements, controls, and repeat procedure |
| Collect and inspect data, including uncertainty | Raw trial record, calculated periods, graph, and discussion of variation and possible bias |
| Construct a model and state assumptions | Explanation of the simple-pendulum model, its assumptions, and the T²–L relation |
| Compare predictions with observations | T and T² plots, fitted-line interpretation, residual inspection, and bounded conclusion |
| Use an agent while independently checking its work | Failure challenge plus independently checked calculation/source claims and a short agent-use record |
| Transfer the process and explain what remains unknown | Transfer challenge and reflection identify changed assumptions, evidence needed, and next question |

| Dimension | Developing | Competent | Strong |
|---|---|---|---|
| Question | Broad or not testable | Precise and investigable | Reveals a useful distinction or gap |
| Design | Variables unclear | Variables and controls are appropriate | Design anticipates confounders and alternatives |
| Evidence | Data lack context | Data and units are traceable | Uncertainty and limitations are analyzed |
| Model | Formula repeated without meaning | Assumptions and predictions explained | Model is tested, bounded, and compared with alternatives |
| Judgment | Accepts results uncritically | Conclusions match evidence | Actively seeks disconfirming evidence |
| Agent use | Copies output | Verifies important claims | Uses agent critique to improve inquiry and documents errors |
| Creation | Repeats a procedure | Proposes a testable extension | Produces and validates a meaningful new result |

**Minimum completion evidence**
- an investigation plan;
- an initial prediction or explanation completed before agent assistance;
- a traceable data record or a clearly labeled alternative dataset;
- at least one graph or structured analysis;
- a conclusion with limitations;
- a critique of one agent response;
- a transfer challenge.

## 11. Reflection

Write short answers:

- What did you believe before the investigation?
- Which observation most changed or refined your thinking?
- Which assumption mattered most?
- What did the agent get wrong, omit, or help you notice?
- What can you now explain without the agent?
- What question would you investigate next?

## 12. Sources and further study

1. Ling, S. J., Sanny, J., and Moebs, W. (2016). *University Physics Volume 1*. OpenStax, Rice University, §15.4, “Pendulums” (open textbook). This section defines the simple-pendulum idealization, derives the small-angle period equation, and discusses its dependence on length and gravitational acceleration: https://openstax.org/books/university-physics-volume-1/pages/15-4-pendulums
2. Taylor, B. N., and Kuyatt, C. E. (1994). *Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results*, NIST Technical Note 1297, §2, “Classification of Components of Uncertainty.” DOI: https://doi.org/10.6028/NIST.tn.1297. The section distinguishes uncertainty from error and cautions against treating random/systematic labels as a complete classification of uncertainty components: https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-2-classification-components-uncertainty

The numerical value of gravitational acceleration used here is an approximate near-Earth reference value; local effective gravity varies with location and altitude. The ideal period equation is standard introductory mechanics, subject to the assumptions stated above.

**Source-maintenance note:** the OpenStax pendulum derivation and the NIST uncertainty terminology were checked against the cited sections on 2026-11-09. These are source checks, not independent subject-matter review. A qualified reviewer must still assess the full tutorial, its experimental advice, and its suitability for the intended learners before publication.

## 13. Review record

- Authoring status: initial instructional draft
- Subject-matter review: pending
- Learner pilot: pending
- Accessibility review: pending
- Reproducibility check: pending
- Agent-assisted source and structure check: 2026-11-09 (not an independent domain review)
- Subject-matter review: pending
- Learner pilot: pending
- Accessibility review: pending
- Reproducibility check: pending
- Qualified-review date: pending

Do not label this tutorial validated until qualified subject review and a learner pilot have been completed and documented.
