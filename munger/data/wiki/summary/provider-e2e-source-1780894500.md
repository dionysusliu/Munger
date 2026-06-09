# Provider E2E Source 1780894500

## Overview
**Provider E2E Source 1780894500** is an end-to-end (E2E) test data source entry tied to automated validation pipelines. This record captures baseline organizational initialization data used for integration testing, identity resolution, and provider-to-consumer data flow verification.

## Run Metadata
- **Run ID:** `1780894500`
- **Source Type:** E2E Data Provider
- **Execution Context:** Automated integration validation
- **Data Scope:** Corporate entity registration & founder attribution
- **Status:** `Active` *(default for archived run records)*

## Entity Information
- **Founder:** [[Alice Arbor]]
- **Organization:** [[Atlas Dynamics]]
- **Relationship:** [[Alice Arbor]] founded [[Atlas Dynamics]]
- **Use Case:** Serves as a canonical seed dataset for testing organizational hierarchy mapping, founder-to-entity linkage, and registry synchronization workflows.

## Testing & Integration Context
- **Pipeline Stage:** End-to-End Validation
- **Validation Checks:**
  - Founder attribution accuracy
  - Organization creation payload structure
  - Cross-reference consistency with [[Provider Registry]]
- **Failure Handling:** Triggers automated rollback and logs to [[Run Logs Archive]]
- **Dependencies:** [[E2E Testing Framework]], [[Data Provider Schema]]

## See Also
- [[Alice Arbor]]
- [[Atlas Dynamics]]
- [[Run ID 1780894500]]
- [[Provider Registry]]
- [[E2E Testing Framework]]

## Notes
> This page functions as a metadata summary for CI/CD and QA workflows. For raw payload samples, execution traces, or environment-specific configurations, consult the [[Run Logs Archive]] or contact the [[QA Engineering]] team.