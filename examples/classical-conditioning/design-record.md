# Skill application record

Status: assistant-authored demonstration, teacher review pending. This record is
not a production gate result or an empirical evaluation.

## Backwards Design Unit Planner

Input: first-year university learners; one 20-minute Chinese introductory lesson;
identify stimulus/response labels, explain their dependence on learning history,
and distinguish a diagram from data. No participant identifiers.

1. Desired results: the three observable outcomes in `course.zh-CN.md`.
2. Assessment evidence designed first: five labels; one hinge question with a
   reason; transfer to a light cue; an exit question about schematic timings.
3. Learning activities: baseline → pairing → tone-alone test → diagnostic check
   → transfer → exit reflection. Each activity prepares an assessment.
4. Alignment: label recognition is both demonstrated and checked; explanation is
   elicited beyond multiple choice; the limits question is explicitly taught.

The PEBS runtime independently executed this skill in the recorded attempt.
This curated lesson is a separate assistant-authored application of the skill.

## Hinge Question Designer

Input: distinguish a learned eliciting stimulus from its response after pairing;
learners have seen the three phases; respond individually within 90 seconds.
The four options target overlooking learning history, retaining the neutral label,
and reversing stimulus/response. Correct answer: B.

The learner worksheet excludes the key. The teacher key explains each distractor,
requires a reason to check lucky guesses, and provides concrete reteaching actions.
Distractor interpretations are hypotheses pending actual classroom review.
The patched PEBS instructions isolate upstream example answers from this question.

## Dual Coding Designer

Input: the verbal explanation in the lesson; novice learners; offline browser;
no audio, decorative media, complex charts or unverified quantitative claims.

- Representation: a temporal sequence across cue, food and response cards.
- Labels: adjacent to the corresponding event, not in a distant legend.
- Meaningful signals: blue cue, amber food, green response, plus text and borders.
- Presentation: learner-controlled steps, synchronized short caption, no autoplay.
- Accessibility: static transcript, printable overview, native buttons, keyboard
  operation, responsive layout and reduced-motion support.
- Avoid: numeric learning-strength bars, claims that one trial is sufficient,
  visual-learning-style labels, sound effects and unrelated decoration.

## Animation design decision

Motion serves a narrow temporal objective: pause between cue and food, and compare
that sequence with a cue-alone test. A static three-panel chart explains the
categories well, but does not directly enact the pause-before-food prediction
activity. For label memorization alone, use the static alternative instead.

This supports a conditional assistant recommendation for interactive sequencing.
It does not claim static teaching is ineffective or that animation improves scores.
The live runtime did not reach its animation gate, so no runtime PASS is claimed.
The production storyboard remains `rendered=false`; the HTML demo is separately authored.

## References and provenance

Skill SHA, local patch and input file hashes are in `skill-trace.json`.
Gareth Manning, Education Agent Skills, pinned at `6bbbce418f82e11044009c9f3b7373a354de5bd0`,
CC BY-SA 4.0. Concept reference: OpenStax *Psychology 2e*, §6.2.
All figures and educational wording here were created for this example.


## v0.2.0 — continuous scene and formative interaction

The revised implementation uses one illustrated scene so learners track the same
sound source, food and organism across phases. A single requestAnimationFrame
clock drives waves, food entry and response droplets; pause freezes that clock,
and scrubbing deterministically reconstructs every element from the selected time.
The 36-second display schedule is not an experimental timing claim. Two pictured
pairings illustrate repetition without asserting a learning threshold.

Backwards design now maps each lesson goal to an on-page action: observe a phase,
predict before revealing the response, answer a diagnostic question, and transfer
the rule to a light cue. Hinge-question options give distinct explanatory feedback;
a correct choice still asks for a reason. Dual-coding labels remain beside the
stimulus or response, while the observation panel explains the relation. Every
phase distinguishes eliciting stimulus and learning history; food is absent in
the learned tone-alone test. Motion reduction leaves static events and text usable.

Four-language browser checks cover all choices, timeline state, UR/CR distinction,
food absence after learning, changing wave transforms while playing, frozen
transforms while paused, mobile overflow and reduced-motion behavior. Desktop and
mobile screenshots were reviewed before publication. No production engine gate
or real teacher sign-off is asserted by this demonstration revision.
