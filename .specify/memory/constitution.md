<!--
Sync Impact Report:
- Version: 0.0.0 → 1.0.0 (MAJOR - initial constitution establishment)
- Ratified: 2025-10-08
- Last Amended: 2025-10-08
- Added Principles:
  * I. Simplicity First
  * II. User Installation Priority
  * III. No Automated Testing
  * IV. Minimal Documentation
- Added Sections:
  * Development Constraints
  * Architecture Guidelines
- Templates Status:
  * ✅ plan-template.md - updated Constitution Check section with concrete principles
  * ✅ spec-template.md - removed test references, changed to "Manual Verification"
  * ✅ tasks-template.md - removed all test tasks, TDD references, and test phases
  * ✅ speckit.tasks.prompt.md - removed test generation logic and TDD workflow
  * ⚠️ Other command prompts - may reference testing but are optional workflows
- Follow-up TODOs: None
-->

# Whisper Typer UI Constitution

## Core Principles

### I. Simplicity First

Every feature MUST use the simplest possible architecture and solution.

- Prefer straightforward, direct implementations over abstraction layers
- No design patterns unless absolutely necessary to solve a real problem
- Avoid frameworks and libraries when native platform capabilities suffice
- Code clarity and maintainability through simplicity, not documentation

**Rationale**: Complexity is the enemy of maintainability in small desktop applications. Simple code is self-documenting and easier to modify.

### II. User Installation Priority

Installation experience MUST be frictionless for end users.

- Single executable or minimal installation steps required
- No complex dependencies that users must manually install
- Cross-platform binaries that work out-of-the-box
- Package formats appropriate for each platform (e.g., .exe, .dmg, .AppImage)

**Rationale**: User adoption depends on effortless installation. Technical users are not the target audience.

### III. No Automated Testing

Automated tests are NOT required for this project.

- Manual testing is sufficient for validation
- Focus development time on features, not test infrastructure
- Quality assurance through direct user feedback
- Testing frameworks and test files are prohibited

**Rationale**: For a small desktop utility with a limited feature set, automated testing overhead exceeds its value. Manual verification is faster and more practical.

### IV. Minimal Documentation

Documentation MUST be minimal and only when essential.

- README with basic usage instructions only
- No API documentation, developer guides, or architecture documents
- Code should be self-explanatory through clear naming and simple structure
- Help resources limited to in-app tooltips or brief command descriptions

**Rationale**: Documentation becomes outdated quickly and adds maintenance burden. Simple, well-written code eliminates most documentation needs.

## Development Constraints

### Code Structure

- Flat, simple directory structure (avoid deep nesting)
- Minimal abstraction layers
- Direct, imperative code over declarative configurations
- Single responsibility per file, but avoid over-fragmentation

## Architecture Guidelines

### Cross-Platform Strategy

- Write once, run anywhere: share maximum code between platforms
- Platform-specific code only when absolutely necessary for native integration
- Use platform-agnostic build tools and packaging
- Test on all target platforms before release

### Dependency Management

- Minimize third-party dependencies
- Evaluate dependency tree depth before adding any library
- Prefer single-purpose libraries over monolithic frameworks
- Bundle dependencies to eliminate user-side installation issues

## Governance

This constitution supersedes all other development practices for the Whisper Typer UI project.

### Amendment Process

- Amendments require clear justification of changed project requirements
- Version bump follows semantic versioning (MAJOR for principle changes, MINOR for new sections, PATCH for clarifications)
- Amendments must propagate to all dependent templates and documentation

### Compliance

- Every feature specification and implementation plan MUST verify compliance with these principles
- Violations require explicit justification and cannot silently proceed
- Complexity introduced must demonstrate clear user value that justifies deviation from simplicity

**Version**: 1.0.0 | **Ratified**: 2025-10-08 | **Last Amended**: 2025-10-08
