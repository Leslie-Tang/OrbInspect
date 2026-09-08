# Code sharing during TAES review

Policy checked on 8 September 2026 against the official
[TAES author instructions](https://ieee-aess.org/publications/transactions-aes/author-information)
and [IEEE research reproducibility guidance](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/).

## Policy and interpretation

- TAES uses single-anonymous review: reviewers know the authors' identities.
  An author-identifying GitHub repository is therefore not inherently
  inconsistent with this review model. The author instructions do not provide
  a separate GitHub-specific approval rule.
- TAES permits supplementary code, data and accompanying documents. Its
  instructions call for references to the supplementary material in the paper,
  a README, and provision of technical supplementary content at submission
  for peer review.
- IEEE encourages authors to share code and supporting research outputs in
  online repositories. A GitHub link can complement, but should not replace,
  the versioned supplementary material submitted for review.

## Recommended release contents for this paper

1. The project's ROS 2 implementation, not merely a link to upstream ROS 2.
2. A frozen release/tag or commit corresponding to the submitted manuscript.
3. Dependencies, installation and execution instructions, experiment
   configurations, and scripts/source data needed to reproduce the reported
   tables and figures.
4. A clear separation between current required-target offline ADP results and
   the historical ROS 2 survey demonstration. Do not imply that the historical
   80% coverage run validates the current nine-target objective.
5. An explicit licence and verified third-party redistribution rights before
   describing the release as open source. Public visibility alone is not a
   reuse licence. Do not disclose credentials or private development material.

An archival identifier can supplement the GitHub development URL; it is a
durability recommendation, not a GitHub-specific TAES submission requirement.

No repository was published, made public, or linked in the manuscript during
this revision. The intended public release URL, release identifier and licence
remain author decisions. The existing commented availability section was not
enabled, because public availability has not been established for that release.

## Additional submission check

The TAES author instructions require disclosure of AI-generated article content
in the acknowledgments, identifying the system and affected content. The
authors should review the actual assistance used for text, figures and code
and provide an accurate disclosure before submission. No disclosure text was
invented or inserted in this revision.
