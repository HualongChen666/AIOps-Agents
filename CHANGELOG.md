# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Core microservices: agent orchestration, alert, audit, repair.
- Add-on microservices: RAG, LLM router, metrics monitoring, topology, and 35 others.
- RAG pipeline with abstract chunking, embedding, retrieval, rerank and fusion strategies.
- Prometheus webhook → approval → repair → audit end-to-end flow.
- SDK (Python), CLI and example clients.
- Docker Compose, K8s manifests and Helm charts.

### Changed

- Converted RAG base classes from `raise NotImplementedError` to `ABC` + `@abstractmethod`.
- Normalized bare `except Exception` usage to typed exception handling.
- Cleaned `placeholder` text occurrences across the codebase.

### Security

- Removed stray temp files and artifacts from the repository.
- Standardized `.env.example` and configuration templates.

## [0.1.0] - 2026-07-30

### Added

- Initial public commit.
- FastAPI API, core services, tests and documentation.

[Unreleased]: https://github.com/HualongChen666/AIOps-Agents/compare/0.1.0...HEAD
[0.1.0]: https://github.com/HualongChen666/AIOps-Agents/releases/tag/0.1.0
