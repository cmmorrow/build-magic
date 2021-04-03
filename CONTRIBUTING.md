# Contributing to build-magic

:wave: Welcome and thanks for your interest in contributing to build-magic!

Please read and abide by the [Github Community Guidelines](https://docs.github.com/en/github/site-policy/github-community-guidelines).

In addition to the Github Community Guidelines, the following set of additional guidelines are provided for contributing to the build-magic project. These guidelines aren't set in stone, so feel free to suggest changes to these guidelines in a pull request.

## Table of Contents

- [Contributing to build-magic](#contributing-to-build-magic)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct :handshake:](#code-of-conduct-handshake)
  - [How Can I Contribute? :question:](#how-can-i-contribute-question)
    - [Reporting a Bug :bug:](#reporting-a-bug-bug)
      - [Considerations Before Submitting a Bug Report :heavy_check_mark:](#considerations-before-submitting-a-bug-report-heavy_check_mark)
      - [Submitting a Bug Report :raising_hand:](#submitting-a-bug-report-raising_hand)
    - [Submitting a Pull Request :spiral_notepad:](#submitting-a-pull-request-spiral_notepad)
    - [Becoming a Maintainer :construction_worker_woman:](#becoming-a-maintainer-construction_worker_woman)
  - [Installing build-magic for Development :construction:](#installing-build-magic-for-development-construction)

## Code of Conduct :handshake:

Please read the build-magic [Code of Conduct](https://github.com/cmmorrow/build-magic/blob/main/CODE_OF_CONDUCT.md) before creating an issue, submitting a pull request, or leaving a comment. Anyone involved with build-magic is expected to behave in accordance with the Code of Conduct. Ignorance is not an excuse.

## How Can I Contribute? :question:

### Reporting a Bug :bug:

Thank you for wanting to make build-magic better. A project like build-magic is difficult to debug with automated tests alone, so your feedback is appreciated. If you believe you've found a bug, you can create an issue and select the Bug Report template. You can find the build-magic Issue Tracker [here](https://github.com/cmmorrow/build-magic/issues).

#### Considerations Before Submitting a Bug Report :heavy_check_mark:

Before creating a new Bug Report, please consider the following questions:

- **What version of build-magic am I using?** If you are using an older version, it's possible the bug you've discovered was fixed in a newer version. Please upgrade to the newest version of build-magic and check to make sure the bug is still reproducible in the newest version before creating a Bug Report.
- **Is the bug reproducible?** Can you get the bug to appear a second and third time? Can you write out detailed instructions on how to reliably reproduce the bug? If the answer is yes to all of these questions, you have a good case for creating a Bug Report.
- **Has the bug I've discovered already been reported?** Before creating a new Bug Report, please check the [Issue Tracker](https://github.com/cmmorrow/build-magic/issues) to make sure someone hasn't already discovered the same bug.

#### Submitting a Bug Report :raising_hand:

If you have discovered a new, reproducible bug on the newest version of build-magic, please visit the [Issue Tracker](https://github.com/cmmorrow/build-magic/issues) and click "New Issue". On the following page to the right of "Bug Report", click "Get started".

Give an appropriate title for the bug, which should be a short description of the result of the bug. Please fill in all pertinent sections of the template and include screenshots if possible. When finished, click "Submit new issue". A maintainer will respond to you as soon as possible and handler the Issue from that point forward.

The maintainers will do their best to resolve your bug in a timely manner. If a maintainer has any questions, they will post a reply in the Issue. Please respect the maintainer's time and respond as soon as possible. If you do not reply within a week, your Issue may be moved into the backlog or closed.

### Submitting a Pull Request :spiral_notepad:

You might be inclined to help make build-magic better by making a code change. This is a great idea! We accept pull requests from non-contributors (any one that isn't an official Contributor to build-magic according to Github), but please be aware of the following acceptance guidelines:

- **Only pull requests associated with an open issue will be considered.** For instance, if you created a Bug Report and think you can fix the problem, please leave a comment in the Issue stating your intention to work on the Issue. A maintainer will assign the Issue to you and you can make a pull request when your work is complete.
- **All tests and flake8 linting must pass before a pull request can be approved and merged.** If you are fixing a bug, make sure your change didn't break any existing tests, and if so, fix them before submitting a pull request. Be sure to add new tests that cover your bug fix to make sure the same bug won't show up again. Keep in mind, if your pull request causes more than a minor drop in code coverage, a maintainer might ask you to add tests that improve the coverage and mark your pull request as "Needs Work".
- **Provide Docstrings for any new modules, classes, methods, or functions.** [PEP 8](https://www.python.org/dev/peps/pep-0008/#documentation-strings) specifies that all public modules, classes, methods, and functions should have a docstring. Please stick to the reStructuredText docstring style used throughout the code base.
- **Avoid using anti-patterns.** You can reference [The Little Book of Python Anti-Patterns](https://docs.quantifiedcode.com/python-anti-patterns/) if you aren't sure what might count as an anti-pattern.
- **Do your best to write clean, readable code.** As developers, we spend a lot of time reading other developer's code. Do your best to keep your code readable by using appropriate variable and function names, avoiding non-trivial one-line conditional statements, writing small functions that do one thing well, and make good use of code reuse. When in doubt, strive for expressive, succinct code.
- **Stick to the existing architecture.** Please don't add new modules or classes without first consulting with a maintainer. If you want to add a new module or class, leave a comment in the issue about the design for your change.

### Becoming a Maintainer :construction_worker_woman:

The build-magic project is maintained by some awesome volunteers. We'd love to have you join us! If you can dedicate at least 5 hours a month to responding to new feature requests and Bug Reports, participate in code review, and work on code changes, please send an email to [cmmorrow@gmail.com](mailto:cmmorrow@gmail.com).

## Installing build-magic for Development :construction:

The build-magic project is written in Python. First, create a new virtual environment for development with `python3 -m venv /path/to/new/virtual/environment`. Alternatively, you can create a virtual environment with `conda` or `virtualenv`. Be sure to activate your virtual environment with `source /path/to/new/virtual/environment/bin/activate`. Next, install build-magic with `pip install build-magic`. To use the Docker and Vagrant runners, you will also need to have Docker and Vagrant installed.