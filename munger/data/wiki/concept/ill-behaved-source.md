>  contro

# Ill-Behaved Source

## Definition

An **ill-behaved source** is a data source, system, or information channel that does not conform to expected standards, protocols, or reliability criteria. It produces outputs that are inconsistent, incomplete, unpredictable, or otherwise problematic for processing, analysis, or consumption. The term is commonly used in data engineering, signal processing, journalism, and systems design to describe sources that require special handling or validation before their outputs can be trusted or used effectively.

## Key Characteristics

- **Inconsistent formatting** – Data arrives in varying structures or schemas
- **Unreliable availability** – Source goes offline or becomes unresponsive without warning
- **Incomplete outputs** – Missing fields, truncated records, or partial transmissions
- **Noise and errors** – Contains high levels of irrelevant or corrupted information
- **Non-standard protocols** – Uses proprietary or undocumented interfaces
- **Lack of versioning** – Changes behavior between requests without notice
- **Rate limiting or throttling** – Imposes unpredictable access restrictions

## Examples

### 1. Web Scraping
A poorly maintained public website that changes its HTML structure weekly, returns 404 errors intermittently, and sometimes serves empty pages — this is an ill-behaved source for any data extraction pipeline.

### 2. User-Generated Content
A social media API that occasionally returns malformed JSON, has undocumented rate limits, and removes fields without deprecation warnings. Developers must implement extensive error handling.

### 3. Sensor Networks
An IoT temperature sensor that sends readings in random units (sometimes Celsius, sometimes Fahrenheit) and occasionally transmits corrupted packets due to interference.

### 4. Legacy Databases
An old mainframe system that outputs EBCDIC-encoded data, uses fixed-width fields with undocumented padding rules, and crashes under moderate query loads.

### 5. News Sources
A wire service that publishes breaking stories with contradictory facts in successive updates, uses inconsistent bylines, and occasionally retracts articles without clear notice.

## Related Mental Models

- [[Garbage In, Garbage Out]] – The principle that flawed input inevitably produces flawed output, making source quality critical
- [[Chesterton's Fence]] – Before "fixing" an ill-behaved source, understand why it behaves that way (often due to historical constraints)
- [[Robustness Principle]] – "Be conservative in what you send, be liberal in what you accept" — a design philosophy for handling ill-behaved sources
- [[Normal Accident Theory]] – Complex systems inevitably produce failures, and ill-behaved sources are often symptoms of underlying complexity
- [[Satisficing]] – Accepting that perfect source behavior is impossible; instead, design for "good enough" handling
- [[Black Swan]] – Ill-behaved sources can produce rare, high-impact anomalies that break assumptions
- [[Technical Debt]] – Quick fixes for ill-behaved sources accumulate into long-term maintenance burdens

## Mitigation Strategies

- **Input validation** – Sanitize and verify all data before processing
- **Graceful degradation** – Design systems to function partially when sources misbehave
- **Circuit breakers** – Automatically stop requesting from sources that exceed error thresholds
- **Idempotent processing** – Ensure repeated processing of same input yields same result
- **Observability** – Monitor source behavior for patterns of ill behavior

## See Also

- [[Data Quality]]
- [[System Reliability]]
- [[Error Handling]]
- [[Anti-Fragile Systems]]
- [[Dirty Data]]