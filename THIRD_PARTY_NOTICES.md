# Attribution and license boundaries

The root MIT license covers original PEBS code and documentation. It does not
relicense upstream teaching skills, research publications, or imported files.

## Education Agent Skills

- Author: Gareth Manning.
- Source: https://github.com/GarethManning/education-agent-skills
- Pinned revision: `6bbbce418f82e11044009c9f3b7373a354de5bd0`.
- License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- PEBS selects 14 skills through `providers/education-agent-skills/provider.yaml`.
- Three adapted SKILL.md files live under `providers/education-agent-skills/patches/`.
  They retain CC BY-SA 4.0 and include modification notices: cognitive-load policy,
  question/answer consistency and example isolation, and UDL boundary safeguards.
- Unmodified downloads and installed runtime files live in ignored `skills/`;
  the installer preserves upstream license and attribution files.
- The upstream notice is in `LICENSES/CC-BY-SA-4.0.txt`; full legal terms are in
  `LICENSES/CC-BY-SA-4.0-legalcode.txt`.

## PPT Foundry

PEBS can use an independently installed, reviewed and pinned PPT Foundry delivery
checker. The development environment used revision
`e6d47bebba83e5c6f69a6d6922b7571215b441ce` (MIT). Its implementation is not bundled
in this public snapshot. Keep the package's original MIT notice when installing
or redistributing it. See `docs/usage.md` for the runtime contract and limitations.

## Classical-conditioning example

Educational text and storyboard in `examples/classical-conditioning/` are
released under CC BY-SA 4.0, attributed to PEBS contributors. The design applies
the three teaching skills identified in `skill-trace.json`; this is an explicit
licensing choice for the example, not a claim that all model outputs inherit a
prompt's license. HTML/CSS/JavaScript implementation is MIT.

Conceptual reference: OpenStax, *Psychology 2e*, section 6.2,
https://openstax.org/books/psychology-2e/pages/6-2-classical-conditioning.
The example uses original wording and schematic graphics; it does not copy
OpenStax illustrations or represent an actual animal experiment.

## Python dependencies

Dependencies are installed separately from `requirements.txt`; their licenses
remain with their respective authors. No credentials, student records, private
course databases, or model account sessions are included in the distribution.
