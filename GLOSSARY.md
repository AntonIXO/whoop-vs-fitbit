# Glossary: what the numbers mean

A plain-English companion to [the article](draft.md). The original Russian version is preserved as `GLOSSARY.ru.original.md`. Definitions below distinguish what a wearable reports from what a reference instrument establishes.

## 1. Sleep measures

### TST — total sleep time

The time the device classifies as sleep: light + deep + REM. It excludes periods classified as awake; it does not independently establish how long you truly slept.

### TIB — time in bed

The recorded interval associated with the night, including wake within that interval. With consistent interval definitions, TIB is at least as large as TST. Vendor exports can differ in how they define the interval.

### Sleep efficiency

$$\mathrm{efficiency}=100\%\times\frac{TST}{TIB}.$$

The share of the recorded night classified as sleep. This depends on both sleep detection and the definition of the night boundary.

### Sleep stages

| Label | Meaning | Common PSG mapping |
|---|---|---|
| Awake | Wakefulness within the recorded interval | Wake |
| Light | Lighter non-REM sleep | N1 + N2 |
| Deep | Slow-wave sleep | N3 |
| REM | Rapid-eye-movement sleep | REM |

A wrist wearable's stage is a classifier output based on indirect signals, not a direct EEG measurement. PSG uses EEG and other physiological signals to score sleep stages.[13]

### Deep-sleep share

$$\mathrm{deep\ share}=\frac{\mathrm{deep\ minutes}}{TST}.$$

This separates a stage's proportion from the overall duration of the night. It does not remove measurement error or all dependence on duration. The mean of nightly shares need not equal the ratio of mean deep minutes to mean TST.

### Onset / offset

The reported start and end of the sleep interval. In this project, a positive onset difference means WHOOP places the start later than Fitbit. It is a difference between device timestamps, not a reference measurement of actual sleep onset.

## 2. Heart-rate measures

### RHR — resting heart rate

A device's estimate of resting heart rate, in beats per minute (bpm). The sampling window and estimation rule depend on the vendor; it is not necessarily the lowest observed HR.

### HRV / RMSSD — heart-rate variability

RMSSD summarises successive beat-interval differences:

$$\mathrm{RMSSD}=\sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1}(RR_{i+1}-RR_i)^2},$$

where $RR_i$ is a beat interval in milliseconds. Interpretation requires suitable, artefact-controlled intervals and a defined recording context. Higher is not universally better; a single value does not diagnose recovery or illness.

### HR nadir

The lowest recorded HR in a specified interval. Its value depends on sampling, smoothing, and artefacts; it is not a direct measure of “depth of recovery”.

### Minutes above 120 / 140 bpm

Counts of recorded minutes above fixed HR thresholds. Useful descriptive summaries, but not personalised intensity zones, verified full-day exposure, or complete TRIMP inputs.

### Heart-rate reserve

$$HRR=HR_{\max}-HR_{\mathrm{rest}},\qquad h=\frac{HR-HR_{\mathrm{rest}}}{HRR}.$$

$HRR$ is a difference in bpm; $h$ is a dimensionless fraction of that reserve. Reliable interpretation requires appropriate maximum and resting HR estimates. WHOOP documents HRR-based display zones but says manual zone changes do not directly determine Strain.[2]

## 3. Training load and WHOOP scores

### TRIMP — training impulse

A family of internal training-load measures combining duration with cardiovascular intensity. Banister-style TRIMP uses duration, relative HR, and an exponential intensity weighting; zone-based methods sum weighted time in intensity bands. They are different formulations, not interchangeable scores.[1]

Session-average HR loses information about intervals and recovery periods. Applying a nonlinear weighting to average HR is generally not equivalent to applying it to each sample and then adding the results.

### Internal versus external load

External load describes work performed, such as distance, speed, or power. Internal load describes the physiological response to that work. A TRIMP-like score need not rank days the same way as steps or estimated energy expenditure.[1]

### Day Strain

WHOOP's proprietary **0–21**, nonlinear score of cardiovascular and supported muscular load. It includes more than formal workouts. The complete mapping and weights are not published.[3]

The API represents Strain on physiological cycles; a current consumer explainer describes midnight resets. For historical exports, establish the actual interval and date-assignment rule rather than assuming these representations are identical.[4][3]

### Activity / session Strain

WHOOP's load score for an individual workout. Displayed session Strains must not be arithmetically added to reconstruct Day Strain because the score is nonlinear.[3]

### Muscular load

WHOOP's estimate of the strength-related work that HR alone can underrepresent. Strength Trainer incorporated muscular load into Strain on WHOOP 4.0 in **April 2023**; automatic estimation expanded to more activity types in 2026.[11][5]

### Recovery

WHOOP's proprietary recovery score, shown as a percentage. In this article it is analysed as a vendor output, not a directly measured physiological quantity. Correlation with RHR establishes overlap, not equivalence or incremental usefulness.

### MVPA

Moderate-to-vigorous physical activity. Here, `mvpa` is the existing export's moderate-plus-vigorous minute summary. It must not be silently relabelled as Fitbit Active Zone Minutes, which is a different weighted measure.

## 4. Statistics

### Spearman's ρ

Rank correlation, from −1 to +1. A positive value means larger values in one series tend to accompany larger values in the other. It describes monotonic association, not equality, causation, or agreement with truth.

There is no universal threshold below which a relationship becomes “no association”. Interpretation depends on uncertainty, measurement error, restricted range, and the question being asked. Strictly increasing transformations preserve ranks, apart from effects such as rounding and ties.

### p-value

Under a specified null model, the probability of obtaining a test statistic at least as extreme as the observed one. It is **not** the probability that the finding is due to chance or that the null hypothesis is true.

The original analyses use block-based permutation methods to retain some serial structure while disrupting the relationship between series. Block size, missing days, and the chosen null remain assumptions.

### Multiple testing / q-value

When many hypotheses are screened, some small p-values occur by chance. Benjamini–Hochberg adjustment addresses the false-discovery rate across a specified family. In the article's original exploratory family, none of the 32 hypotheses cleared the selected FDR gate. This is not proof that all corresponding effects are zero.

### Bias / mean paired difference

The mean of WHOOP minus Fitbit. Without a reference standard, it is an inter-device offset—not the error of either device. “WHOOP is higher on average” does not mean it is higher on every night.

### Limits of agreement (LoA)

$$\mathrm{LoA}=\overline{d}\pm1.96s_d,$$

where $d$ is the paired difference and $s_d$ its sample standard deviation. These describe the spread of differences under the usual distributional assumptions. They are not a confidence interval for the mean bias or a guarantee that 95% of future nights will fall within them.

### Bland–Altman plot

Plots the paired difference against the mean of the two measurements. It exposes systematic offsets, scatter, and differences that change with measurement magnitude.

### 95% confidence interval

An interval generated by a procedure intended to cover the target parameter in 95% of repeated samples under its assumptions. It is not the range containing 95% of individual measurements. The article's mean sleep-gap intervals use moving-block bootstrap resampling.

### Cohen's κ

Agreement between categorical classifications beyond the agreement expected from their marginal frequencies. Zero means no agreement beyond that expectation; one means perfect agreement. It is not directly comparable to correlation between nightly stage totals and does not impose a universal ceiling on that correlation.

### Lag-one autocorrelation

Association between observations one time step apart. For a daily series, calendar adjacency must be distinguished from adjacent rows when dates are missing. A value near zero does not establish white noise, randomness, or lack of useful information.

## 5. Validation and software versions

### PSG — polysomnography

A reference sleep assessment using EEG, eye movements, muscle activity, and other physiological recordings. It can be used while someone wears several consumer devices. The Schyvens study used two to four wearables per participant.[13]

### Sensitivity / specificity

For sleep/wake classification, sensitivity is the proportion of reference sleep epochs identified as sleep; specificity is the proportion of reference wake epochs identified as wake. High sensitivity alone does not establish good wake detection or accurate multistage classification.

### Algorithm drift

A change in recorded values caused by a change in processing rather than necessarily a change in the person. Distinguish firmware, cloud algorithms, app presentation, personal calibration, and export rules. A release announcement is not proof of deployment to a particular account.

### Personalised calibration

An unchanged algorithm can produce different scores when its personal baseline or maximum-HR setting changes. That is different from a vendor releasing a new algorithm.

### Descriptive association versus validation

A correlation between two wearable outputs describes their relationship. Internal consistency checks ask whether a system agrees with its own inputs and components. Independent validation asks whether it agrees with an appropriate reference. These are different levels of evidence.

## Sources

[1] https://www.mdpi.com/2227-7080/11/3/79
[2] https://support.whoop.com/s/article/What-is-Max-Heart-Rate-and-How-Do-I-Adjust-It
[3] https://www.whoop.com/us/en/thelocker/how-does-whoop-strain-work-101
[4] https://developer.whoop.com/docs/developing/user-data/cycle
[5] https://www.whoop.com/us/en/thelocker/2026-whats-new
[11] https://www.whoop.com/us/en/press-center/whoop-introduces-strength-trainer-becomes-first-wearable-to-measure-muscular
[13] https://pmc.ncbi.nlm.nih.gov/articles/PMC12038347
