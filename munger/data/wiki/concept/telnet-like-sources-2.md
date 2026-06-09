>       

# Telnet-like Sources

**Telnet-like sources** refer to legacy data systems that require interactive terminal sessions—typically via Telnet, SSH, or proprietary terminal emulators—to extract or query data. Unlike modern REST APIs or SQL databases, these sources often present data only through a character-based user interface (a “green screen”), and automated data retrieval depends on simulating human keystrokes or screen-scraping techniques.

Common environments include IBM mainframes (e.g., via TN3270), AS/400 systems, Unix shell‑based applications, and older industrial or financial systems that expose no structured data interface.

## Characteristics

- **Terminal‑based access**: No direct data API; interaction is via command‑line or menu‑driven screens.
- **Screen‑oriented output**: Data is formatted for display (e.g., fixed‑width fields, headers, footers).
- **Session statefulness**: Many require login, navigation, and session management.
- **Limited automation support**: No native batch extraction; custom scripts or middleware are needed.

## Examples

| Source Type | Typical Access Method | Use Case |
|-------------|-----------------------|----------|
| IBM Mainframe (z/OS) | TN3270 | Retrieving transaction logs or customer records via a CICS application |
| AS/400 (IBM i) | 5250 terminal emulation | Extracting inventory data from a legacy ERP system |
| Unix Shell Application | SSH | Pulling reports from a command‑line tool that has no export option |
| Industrial Control System | Telnet or serial terminal | Reading sensor data from a PLC that only displays values on a terminal |

## Common Extraction Approaches

1. **Screen Scraping** – Parse the character output of terminal screens to extract structured data.
2. **Keystroke Automation** – Script interactions (e.g., using Expect, AutoIt, or Python’s `pexpect`) to navigate menus and capture printed output.
3. **Terminal Emulation APIs** – Use libraries that support Telnet/SSH and can render and parse terminal screens (e.g., Curses, JSCH).
4. **Middleware Gateways** – Deploy products (e.g., Attunity, Software AG) that expose legacy screens as web services or JDBC sources.

## Related Mental Models

- [[Screen Scraping]] – The core technique for extracting data from visual displays rather than structured interfaces.
- [[Legacy System Integration]] – The broader challenge of connecting modern data pipelines to old, often closed systems.
- [[Terminal Emulation]] – Software that mimics a physical terminal to interact with host systems.
- [[Green Screen]] – Common nickname for character‑based mainframe/AS/400 interfaces.
- [[Data Lineage]] – Understanding how data from such fragile sources flows into downstream systems; difficult to trace.
- [[Technical Debt]] – Telnet‑like sources are a prime example of technical debt that increases extraction complexity and maintenance cost.

## See Also

- [[ETL from Mainframe]]
- [[Expect Scripting for Data Extraction]]
- [[Mainframe Modernization]]